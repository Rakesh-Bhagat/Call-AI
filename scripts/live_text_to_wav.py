import os, asyncio, wave
from google import genai
from dotenv import load_dotenv
from google.genai import types

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
MODEL = os.environ["LIVE_MODEL"]

config = types.LiveConnectConfig(response_modalities=['AUDIO'])

async def main():
    chunks = []
    async with client.aio.live.connect(model=MODEL, config=config) as session:
        await session.send_client_content(
            turns = types.Content(role="user", parts=[types.Part(text="Say hello and introduce yourself in one sentence")]),
            turn_complete=True,
        )
        async for msg in session.receive():
            sc = msg.server_content
            if sc and sc.model_turn:
                for part in sc.model_turn.parts:
                    if part.inline_data:
                        chunks.append(part.inline_data.data)
                        print("chunk: ", len(part.inline_data.data), "bytes", part.inline_data.mime_type)
            if sc and sc.turn_complete:
                break

    with wave.open("out.wav", "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(24000)
        f.writeframes(b"".join(chunks))
    print("saved out.wav")

asyncio.run(main())