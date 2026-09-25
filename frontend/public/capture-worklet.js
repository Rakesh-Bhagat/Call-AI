// Runs on the audio thread. Turns mic Float32 samples into 16-bit PCM
// and posts 40 ms chunks (640 samples @ 16 kHz) to the main thread.
class CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.buf = new Int16Array(640);
    this.n = 0;
  }

  process(inputs) {
    const channel = inputs[0][0];
    if (!channel) return true;

    for (let i = 0; i < channel.length; i++) {
      const s = Math.max(-1, Math.min(1, channel[i]));
      this.buf[this.n++] = s < 0 ? s * 0x8000 : s * 0x7fff;
      if (this.n === this.buf.length) {
        const out = this.buf.buffer.slice(0);
        this.port.postMessage(out, [out]);
        this.n = 0;
      }
    }
    return true;
  }
}

registerProcessor("capture", CaptureProcessor);
