import asyncio
from types import SimpleNamespace as NS
from app.live.call import CallSession


class FakeTransport:
    def __init__(self):
          self.audio, self.events = [], []
          self.cleared = 0
          self.finished = 0

    async def receive_audio(self):
          return None

    async def send_audio(self, pcm):
          self.audio.append(pcm)

    async def clear_playback(self):
          self.cleared += 1

    async def send_event(self, event):
          self.events.append(event)

    async def finish(self):
          self.finished += 1


class FakeGemini:
    def __init__(self):
          self.responses = []

    async def send_tool_response(self, function_responses):
          self.responses.extend(function_responses)


def make_call():
    call = CallSession(FakeTransport())
    call.session = FakeGemini()
    return call


def tool_call(name, **args):
    return NS(function_calls=[NS(id="1", name=name, args=args)])


def content(audio=False, turn_complete=False, interrupted=False):
    parts = [NS(inline_data=NS(data=b"\x00\x00"))] if audio else []
    return NS(
        interrupted=interrupted,
        input_transcription=None,
        output_transcription=None,
        turn_complete=turn_complete,
        model_turn=NS(parts=parts) if parts else None,
    )


def test_call_ends_only_after_the_goodbye_audio():
    async def scenario():
        call = make_call()
        await call._handle_tool_call(tool_call("end_call"))
        await call._handle_server_content(content(turn_complete=True))
        assert call.transport.finished == 0
        await call._handle_server_content(content(audio=True))
        await call._handle_server_content(content(turn_complete=True))
        assert call.transport.finished == 1
        await call._handle_server_content(content(turn_complete=True))
        assert call.transport.finished == 1
        call._watchdog.cancel()

    asyncio.run(scenario())


def test_escalation_notifies_the_transport_once():
    async def scenario():
        call = make_call()
        await call._handle_tool_call(tool_call("escalate_to_agent", reason="fraud report"))
        await call._handle_tool_call(tool_call("escalate_to_agent", reason="again"))
        assert call.transport.events == [{"type": "escalated", "reason": "fraud report"}]
        call._watchdog.cancel()

    asyncio.run(scenario())


def test_barge_in_clears_playback():
    async def scenario():
        call = make_call()
        await call._handle_server_content(content(interrupted=True))
        assert call.transport.cleared == 1

    asyncio.run(scenario())