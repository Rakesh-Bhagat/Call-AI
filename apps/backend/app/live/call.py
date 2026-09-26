import asyncio
from google.genai import types
from app.agent.context import CallContext
from app.agent.tools import REGISTRY
from app.live.session import connect
from app.live.transport import Transport

FAREWELL_TIMEOUT_SECONDS = 20

class CallSession:
    def __init__(self, transport: Transport):
        self.transport = transport
        self.ctx = CallContext()
        self.session = None
        self.ending = False
        self.farewell_heard = False
        self.finished = False
        self._watchdog: asyncio.Task | None = None

    async def run(self) -> None:
        async with connect() as session:
            self.session = session
            tasks = [
                asyncio.create_task(self._pump_in()),
                asyncio.create_task(self._pump_out())
            ]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in tasks:
                task.cancel()
            if self._watchdog:
                self._watchdog.cancel()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    print("TASK ERROR: ", repr(result), flush=True)


    async def _pump_in(self) -> None:
        while (data := await self.transport.receive_audio()) is not None:
            await self.session.send_realtime_input(
                audio= types.Blob(data=data, mime_type= "audio/pcm;rate=16000")
            )

    async def _pump_out(self) -> None:
        while True:
            async for msg in self.session.receive():
                if msg.tool_call:
                    await self._handle_tool_call(msg.tool_call)
                if msg.go_away:
                    print("GO AWAY: ", msg.go_away)
                if msg.server_content:
                    await self._handle_server_content(msg.server_content)

    async def _handle_tool_call(self, tool_call) -> None:
        responses = []
        for fc in tool_call.function_calls:
            fn = REGISTRY.get(fc.name)
            try:
                result = fn(self.ctx, **(fc.args or {})) if fn else {"error": f"Unknown tool call {fc.name}"}
            except Exception as e:
                result = {"error": f"Tool failed: {e}"}
            print("TOOL:", fc.name, fc.args, "->", result, flush=True)
            responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response=result))
        await self.session.send_tool_response(function_responses=responses)
        if (self.ctx.escalated or self.ctx.ended) and not self.ending:
            await self._begin_ending()

    async def _handle_server_content(self, sc) -> None:
        if sc.interrupted:
            print("INTERRUPTED")
            await self.transport.clear_playback()
        if sc.input_transcription and sc.input_transcription.text:
            print("USER: ", sc.input_transcription.text)
            await self.transport.send_event({
                "type": "transcript",
                "role": "user",
                "text": sc.input_transcription.text
            })
        if sc.output_transcription and sc.output_transcription.text:
            print("BOT: ",sc.output_transcription.text)
            await self.transport.send_event({
                "type": "transcript",
                "role": "assistant", 
                "text": sc.output_transcription.text
            })

        if sc.turn_complete:
            print("TURN COMPLETE")
            if self.ending and self.farewell_heard:
                await self._finish()
        if sc.model_turn:
            for part in sc.model_turn.parts:
                if part.inline_data:
                    if self.ending:
                        self.farewell_heard = True
                    await self.transport.send_audio(part.inline_data.data)

    async def _begin_ending(self) -> None:
        self.ending = True
        if self.ctx.escalated:
            await self.transport.send_event({"type": "escalated", "reason": self.ctx.escalation_reason})
        self._watchdog = asyncio.create_task(self._force_finish())

    async def _force_finish(self) -> None:
        await asyncio.sleep(FAREWELL_TIMEOUT_SECONDS)
        await self._finish()
    
    async def _finish(self) -> None:
        if self.finished: 
            return
        self.finished = True
        await self.transport.finish()