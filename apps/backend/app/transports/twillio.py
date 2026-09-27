import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect
from app.audio.codec import pcm16_to_ulaw_b64, ulaw_b64_to_pcm16
from app.audio.resample import Resampler

MARK_TIMEOUT_SECONDS=10

class TwillioTransport:
    speak_first = True
    def __init__(self, ws: WebSocket):
        self.ws = ws
        self.stream_sid: str | None = None
        self.call_sid: str | None = None
        self._up = Resampler(8000,16000)
        self._down = Resampler(24000,8000)
        self._started = asyncio.Event()
        self._mark_echoed = asyncio.Event()

    async def _send(self, payload: dict) -> None:
        await self._started.wait()
        await self.ws.send_text(json.dumps({**payload, "streamSid": self.stream_sid}))

    async def receive_audio(self) -> bytes | None:
        while True:
            try:
                message = json.loads(await self.ws.receive_text())
            except WebSocketDisconnect:
                return None

            event = message.get("event")
            if event == "start":
                self.stream_sid = message["start"]["streamSid"]
                self.call_sid = message["start"]["callSid"]
                self._started.set()
            elif event == "media":
                return self._up.process(ulaw_b64_to_pcm16(message["media"]["payload"]))
            elif event == "mark":
                self._mark_echoed.set()
            elif event == "stop":
                return None

    async def send_audio(self, pcm24k: bytes) -> None:
        payload = pcm16_to_ulaw_b64(self._down.process(pcm24k))
        await self._send({"event": "media", "media": {"payload": payload}})

    async def clear_playback(self) -> None:
        await self._send({"event": "clear"})

    async def send_event(self, event: dict) -> None:
        if event["type"] == "escalated":
            print("ESCALATED:", self.call_sid, event["reason"], flush=True)

    async def finish(self) -> None:
        self._mark_echoed.clear()
        await self._send({"event": "mark", "mark": {"name": "goodbye"}})
        try:
            await asyncio.wait_for(self._mark_echoed.wait(), MARK_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            pass
        await self.ws.close()