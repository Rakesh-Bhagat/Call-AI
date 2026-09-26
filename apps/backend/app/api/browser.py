import asyncio
import wave
from pathlib import Path
from fastapi import APIRouter, WebSocket
from google.genai import types
from app.live.session import connect
from app.agent.context import CallContext
from app.agent.tools import REGISTRY

router = APIRouter()

# Debug: keep the audio we receive from the browser so we can listen to / replay it.
DEBUG_WAV = Path("logs/last_call_in.wav")

@router.websocket("/ws/browser")
async def browser_ws(ws: WebSocket):
    await ws.accept()
    recorded = bytearray()
    async with connect() as session:
        ctx = CallContext()
        ending = False
        farewell_heard = False
        call_ended = False
        watchdog = None

        async def end_call():
            nonlocal call_ended
            if call_ended:
                return
            call_ended = True
            await ws.send_json({"type": "call_ended"})

        async def force_end():
            await asyncio.sleep(20)
            await end_call()

        async def browser_to_gemini():
            while True:
                data = await ws.receive_bytes()
                recorded.extend(data)
                await session.send_realtime_input(
                    audio = types.Blob(data=data, mime_type="audio/pcm;rate=16000")
                )

        async def gemini_to_browser():
            nonlocal ending, farewell_heard, watchdog
            while True:
                async for msg in session.receive():
                    if msg.tool_call:
                        responses = []
                        for fc in msg.tool_call.function_calls:
                            fn = REGISTRY.get(fc.name)
                            try:
                                result = fn(ctx, **(fc.args or {})) if fn else {"error": f"Unknown tool {fc.name}"}
                            except Exception as e:
                                result = {"error": f"Tool failed: {e}"}
                            print("TOOL:", fc.name, fc.args, "->", result, flush=True)
                            responses.append(types.FunctionResponse(id=fc.id, name=fc.name, response=result))

                        await session.send_tool_response(function_responses=responses)
                        if (ctx.escalated or ctx.ended) and not ending:
                            ending = True
                            if ctx.escalated:
                                await ws.send_json({"type": "escalated", "reason": ctx.escalation_reason})
                            watchdog = asyncio.create_task(force_end())
                    if msg.go_away:
                        print("GO_AWAY:", msg.go_away)
                    sc = msg.server_content
                    if not sc:
                        # print("MSG:", str(msg)[:200], flush=True)
                        continue
                    if sc.interrupted:
                        print("INTERRUPTED")
                        await ws.send_json({"type": "interrupted"})
                    if sc.input_transcription and sc.input_transcription.text:
                        print("USER:", sc.input_transcription.text)
                        await ws.send_json({"type": "transcript", "role": "user", "text": sc.input_transcription.text})
                    if sc.output_transcription and sc.output_transcription.text:
                        print("BOT:", sc.output_transcription.text)
                        await ws.send_json({"type": "transcript", "role": "assistant", "text": sc.output_transcription.text})
                    if sc.turn_complete:
                        print("TURN COMPLETE")
                        if ending and farewell_heard:
                            await end_call()
                    if sc.model_turn:
                        for p in sc.model_turn.parts:
                            if p.inline_data:
                                if ending:
                                    farewell_heard = True
                                await ws.send_bytes(p.inline_data.data)

        tasks = [asyncio.create_task(browser_to_gemini()), asyncio.create_task(gemini_to_browser())]

        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        if watchdog:
            watchdog.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, Exception) and not isinstance(r, asyncio.CancelledError):
                print("TASK ERROR:", repr(r), flush=True)

    if recorded:
        DEBUG_WAV.parent.mkdir(exist_ok=True)
        with wave.open(str(DEBUG_WAV), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(bytes(recorded))
        print(f"saved {DEBUG_WAV} ({len(recorded)} bytes)", flush=True)