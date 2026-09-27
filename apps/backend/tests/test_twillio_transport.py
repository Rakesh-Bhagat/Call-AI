import asyncio
import base64
import json
from app.transports.twillio import TwillioTransport


class FakeWS:
    def __init__(self, incoming):
        self.incoming = [json.dumps(m) for m in incoming]
        self.sent = []

    async def receive_text(self):
        return self.incoming.pop(0)

    async def send_text(self, text):
        self.sent.append(json.loads(text))

    async def close(self):
        pass


START = {"event": "start", "start": {"streamSid": "MZ1", "callSid": "CA1"}}
FRAME = {"event": "media", "media": {"payload": base64.b64encode(bytes([0xFF])
  * 160).decode()}}


def test_inbound_frame_becomes_16khz_pcm_and_stop_ends_the_call():
    async def scenario():
        transport = TwillioTransport(FakeWS([START, FRAME, {"event": "stop"}]))
        pcm = await transport.receive_audio()
        assert pcm is not None
        assert abs(len(pcm) - 640) <= 4
        assert await transport.receive_audio() is None

    asyncio.run(scenario())


def test_outbound_audio_is_an_8khz_mulaw_media_event():
    async def scenario():
        ws = FakeWS([START, FRAME])
        transport = TwillioTransport(ws)
        await transport.receive_audio()
        await transport.send_audio(b"\x00\x00" * 480)
        event = ws.sent[0]
        assert event["event"] == "media"
        assert event["streamSid"] == "MZ1"
        assert abs(len(base64.b64decode(event["media"]["payload"])) - 160) <= 2

    asyncio.run(scenario())