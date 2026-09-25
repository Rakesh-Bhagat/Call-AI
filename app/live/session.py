from google import genai
from google.genai import types
from app.config import settings

client = genai.Client(api_key=settings.gemini_api_key)


def build_config() -> types.LiveConnectConfig:
    return types.LiveConnectConfig(
        response_modalities=['AUDIO'],
        system_instruction="You are a helpful voice assistant. Keep answers short.",
        input_audio_transcription={},
        output_audio_transcription={},
    )

def connect():
    return client.aio.live.connect(model=settings.live_model, config=build_config())