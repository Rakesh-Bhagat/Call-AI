import audioop

class Resampler:
    def __init__(self, src_rate: int, dst_rate: int):
        self.src, self.dst, self._state = src_rate, dst_rate, None

    def process(self, pcm: bytes) -> bytes:
        out, self._state = audioop.ratecv(pcm, 2,1, self.src, self.dst, self._state)
        return out