"use client";

import { useEffect, useRef, useState } from "react";

const WS_URL = process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/browser";
const IN_RATE = 16000;  // what Gemini expects from us
const OUT_RATE = 24000; // what Gemini sends back

type Status = "idle" | "connecting" | "live" | "error";
type Line = { role: "user" | "assistant"; text: string };

export default function Page() {
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState("");
  const [lines, setLines] = useState<Line[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const inCtxRef = useRef<AudioContext | null>(null);
  const outCtxRef = useRef<AudioContext | null>(null);
  const sourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const nextTimeRef = useRef(0);
  const logRef = useRef<HTMLDivElement>(null);
  const statsRef = useRef({ sent: 0, received: 0, peak: 0 });
  const [stats, setStats] = useState({ sent: 0, received: 0, peak: 0 });

  useEffect(() => {
    if (status !== "live") return;
    const id = setInterval(() => {
      setStats({ ...statsRef.current });
      statsRef.current.peak = 0;
    }, 500);
    return () => clearInterval(id);
  }, [status]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [lines]);

  useEffect(() => () => teardown(), []);

  function teardown() {
    wsRef.current?.close();
    streamRef.current?.getTracks().forEach((t) => t.stop());
    inCtxRef.current?.close();
    outCtxRef.current?.close();
    wsRef.current = streamRef.current = inCtxRef.current = outCtxRef.current = null;
    sourcesRef.current.clear();
    nextTimeRef.current = 0;
  }

  // Barge-in: drop everything queued so the bot stops mid-sentence.
  function stopPlayback() {
    sourcesRef.current.forEach((s) => {
      try { s.stop(); } catch {}
    });
    sourcesRef.current.clear();
    nextTimeRef.current = 0;
  }

  // Gemini sends 16-bit PCM @ 24 kHz. Queue each chunk right after the previous one.
  function play(data: ArrayBuffer) {
    const ctx = outCtxRef.current;
    if (!ctx) return;
    const i16 = new Int16Array(data, 0, Math.floor(data.byteLength / 2));
    const f32 = new Float32Array(i16.length);
    for (let i = 0; i < i16.length; i++) f32[i] = i16[i] / 32768;

    const buffer = ctx.createBuffer(1, f32.length, OUT_RATE);
    buffer.copyToChannel(f32, 0);
    const src = ctx.createBufferSource();
    src.buffer = buffer;
    src.connect(ctx.destination);

    const startAt = Math.max(ctx.currentTime, nextTimeRef.current);
    src.start(startAt);
    nextTimeRef.current = startAt + buffer.duration;
    sourcesRef.current.add(src);
    src.onended = () => sourcesRef.current.delete(src);
  }

  function addTranscript(role: Line["role"], text: string) {
    setLines((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === role) {
        return [...prev.slice(0, -1), { role, text: last.text + text }];
      }
      return [...prev, { role, text }];
    });
  }

  async function start() {
    setError("");
    setLines([]);
    setStatus("connecting");
    statsRef.current = { sent: 0, received: 0, peak: 0 };
    setStats({ sent: 0, received: 0, peak: 0 });
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      streamRef.current = stream;

      const outCtx = new AudioContext({ sampleRate: OUT_RATE });
      outCtxRef.current = outCtx;
      await outCtx.resume();

      // Asking for a 16 kHz context makes the browser resample the mic for us.
      const inCtx = new AudioContext({ sampleRate: IN_RATE });
      inCtxRef.current = inCtx;
      await inCtx.resume();
      await inCtx.audioWorklet.addModule("/capture-worklet.js");

      const ws = new WebSocket(WS_URL);
      ws.binaryType = "arraybuffer";
      wsRef.current = ws;

      await new Promise<void>((resolve, reject) => {
        ws.onopen = () => resolve();
        ws.onerror = () => reject(new Error(`Cannot reach backend at ${WS_URL}`));
      });

      ws.onmessage = (e) => {
        if (typeof e.data === "string") {
          const msg = JSON.parse(e.data);
          if (msg.type === "interrupted") stopPlayback();
          else if (msg.type === "transcript") addTranscript(msg.role, msg.text);
        } else {
          statsRef.current.received += (e.data as ArrayBuffer).byteLength;
          play(e.data as ArrayBuffer);
        }
      };
      ws.onclose = () => {
        teardown();
        setStatus((s) => (s === "error" ? s : "idle"));
      };

      const mic = inCtx.createMediaStreamSource(stream);
      const worklet = new AudioWorkletNode(inCtx, "capture");
      worklet.port.onmessage = (e) => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(e.data);
          const samples = new Int16Array(e.data as ArrayBuffer);
          let peak = 0;
          for (let i = 0; i < samples.length; i++) peak = Math.max(peak, Math.abs(samples[i]));
          statsRef.current.sent += samples.byteLength;
          statsRef.current.peak = Math.max(statsRef.current.peak, peak);
        }
      };
      mic.connect(worklet);
      // Some browsers only run a worklet that is wired to the destination, so keep it
      // in the graph through a muted gain node.
      const mute = inCtx.createGain();
      mute.gain.value = 0;
      worklet.connect(mute).connect(inCtx.destination);

      setStatus("live");
    } catch (err) {
      teardown();
      setError(err instanceof Error ? err.message : String(err));
      setStatus("error");
    }
  }

  function stop() {
    teardown();
    setStatus("idle");
  }

  const busy = status === "connecting";
  const live = status === "live";

  return (
    <main>
      <div>
        <h1>Voice Assistant</h1>
        <p className="hint">Use headphones so the assistant doesn&apos;t hear itself. Talk over it to interrupt.</p>
      </div>

      <div className="bar">
        {live ? (
          <button className="stop" onClick={stop}>End call</button>
        ) : (
          <button onClick={start} disabled={busy}>{busy ? "Connecting…" : "Start call"}</button>
        )}
        <span className="status">
          <span className={`dot ${live ? "live" : status === "error" ? "error" : ""}`} />
          {live ? "Listening" : status === "error" ? "Error" : busy ? "Connecting" : "Idle"}
        </span>
      </div>

      {live && (
        <p className="hint" data-testid="stats">
          Sent {Math.round(stats.sent / 1024)} KB · Received {Math.round(stats.received / 1024)} KB · Mic level {Math.round((stats.peak / 32768) * 100)}%
        </p>
      )}

      {error && <p className="error">{error}</p>}

      <div className="log" ref={logRef}>
        {lines.length === 0 ? (
          <p className="empty">Transcript appears here.</p>
        ) : (
          lines.map((l, i) => (
            <div className="line" key={i}>
              <span className="who">{l.role === "user" ? "You" : "Assistant"}</span>
              {l.text}
            </div>
          ))
        )}
      </div>
    </main>
  );
}
