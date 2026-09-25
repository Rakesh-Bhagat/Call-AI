import audioop, base64

def ulaw_b64_to_pcm16(payload_b64: str) -> bytes:
    return audioop.ulaw2lin(base64.b64decode(payload_b64), 2)

def pcm16_to_ulaw_b64(pcm: bytes) -> str:
    return base64.b64encode(audioop.lin2ulaw(pcm, 2)).decode()