from app.audio.codec import ulaw_b64_to_pcm16, pcm16_to_ulaw_b64
from app.audio.resample import Resampler
import base64

def test_twilio_frame_upsamples_to_gemini_rate():
  frame = base64.b64encode(bytes([0xFF]) * 160).decode()
  pcm8k = ulaw_b64_to_pcm16(frame)
  assert len(pcm8k) == 320
  pcm16k = Resampler(8000, 16000).process(pcm8k)
  assert abs(len(pcm16k) - 640) <= 4

def test_gemini_chunk_downsamples_to_twilio_rate():
  pcm24k = b"\x00\x00" * 480
  pcm8k = Resampler(24000, 8000).process(pcm24k)
  assert abs(len(pcm8k) - 320) <= 4
  assert len(base64.b64decode(pcm16_to_ulaw_b64(pcm8k))) == len(pcm8k) // 2