import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

for m in client.models.list():
    actions = m.supported_actions or []
    if "bidiGenerateContent" in actions:
        print(m.name)

