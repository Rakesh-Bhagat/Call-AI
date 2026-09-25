from google import genai
from google.genai import types
from app.config import settings
from app.agent.tools import TOOLS
from app.agent.prompts import build_system_prompt

client = genai.Client(api_key=settings.gemini_api_key)


def build_config() -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        response_modalities=['AUDIO'],
        system_instruction=build_system_prompt(),
        tools=[TOOLS],
        input_audio_transcription={},
        output_audio_transcription={},
    )

def connect():
    return client.aio.live.connect(model=settings.live_model, config=build_config())