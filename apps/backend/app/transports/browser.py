from fastapi import WebSocket, WebSocketDisconnect

class BrowserTransport:
    def __init__(self, ws:WebSocket):
        self.ws = ws
        
    async def receive_audio(self) -> bytes | None:
        try:
            return await self.ws.receive_bytes()
        except WebSocketDisconnect:
            return None

    async def send_audio(self, pcm24k: bytes) -> None:
        await self.ws.send_bytes(pcm24k)

    async def clear_playback(self)-> None:
        await self.ws.send_json({"type": "interrupted"})

    async def send_event(self, event: dict) -> None:
        await self.ws.send_json(event)

    async def finish(self)-> None:
        await self.ws.send_json({"type": "call_ended"})