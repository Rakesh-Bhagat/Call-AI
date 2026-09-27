import type { Metadata } from "next";
import Link from "next/link";
import { OverviewDiagram } from "./diagrams";

export const metadata: Metadata = {
  title: "Architecture — Call AI",
  description: "How Call AI is built: the call loop, the transport abstraction, the audio pipeline, and the security decisions.",
};

const LATENCY = [
  { model: "gemini-2.5-flash-native-audio", seconds: 3.5, selected: false },
  { model: "gemini-3.1-flash-live-preview", seconds: 1.35, selected: false },
  { model: "gemini-3.8-live", seconds: 1.1, selected: true },
];
const MAX_LATENCY = Math.max(...LATENCY.map((l) => l.seconds));

const TOOLS = [
  { name: "verify_customer", input: "mobile last 4 + date of birth", does: "Matches against the customer record and marks the call's context as verified. Every other tool refuses to run until this succeeds." },
  { name: "check_loan_emi", input: "loan type (optional)", does: "EMI amount, next due date, outstanding balance, overdue amount — for the verified caller's own loan only." },
  { name: "check_account_balance", input: "account type (optional)", does: "Savings balance, or a fixed deposit's balance, rate and maturity date." },
  { name: "escalate_to_agent", input: "reason", does: "Arranges a human callback and ends the call. Works even if the caller never verified." },
  { name: "end_call", input: "—", does: "Ends the call when the caller is done, or asks to hang up." },
];

export default function ArchitecturePage() {
  return (
    <div className="doc-wrap">
      <main className="doc-main">
        <div className="doc-intro">
          <h1>How Call AI works</h1>
          <p>
            A voice agent that runs over a browser tab or a real phone call, backed by the same
            code either way. This page covers the request flow, why the transport is a separate
            layer from the agent, the audio format problem a phone call forces on you, and the
            security decisions that matter more than the demo.
          </p>
        </div>

        <nav className="doc-nav" aria-label="Sections">
          <a href="#overview">Overview</a>
          <a href="#flow">Request flow</a>
          <a href="#transport">Transport abstraction</a>
          <a href="#audio">Audio pipeline</a>
          <a href="#security">Security</a>
          <a href="#tools">Tools</a>
          <a href="#latency">Latency</a>
          <a href="#stack">Stack</a>
        </nav>

        <section className="doc-section" id="overview">
          <p className="doc-kicker">01</p>
          <h2>Overview</h2>
          <p>
            One call loop drives both the browser demo and the phone. A <code>CallSession</code>{" "}
            knows nothing about WebSockets, Twilio, or audio formats — it streams audio to Gemini
            Live, dispatches tool calls to the mock loans-and-deposits data, and runs the
            escalate/end-call lifecycle. Everything specific to <em>how</em> the audio arrives sits
            behind a small <code>Transport</code> interface, implemented once for the browser and
            once for Twilio.
          </p>
          <figure className="doc-figure">
            <OverviewDiagram />
            <figcaption>
              One <code>CallSession</code>, one <code>Transport</code> per call. The browser and
              Twilio transports differ only in audio format and protocol framing.
            </figcaption>
          </figure>
        </section>

        <section className="doc-section" id="flow">
          <p className="doc-kicker">02</p>
          <h2>Request flow</h2>
          <p>What actually happens between a caller speaking and the agent replying:</p>
          <ol className="flow-steps">
            <li className="flow-step">
              <span className="flow-num">1</span>
              <div>
                <h4>Caller speaks</h4>
                <p>Raw mic audio in the browser, or 8 kHz μ-law over the phone network via Twilio Media Streams.</p>
              </div>
            </li>
            <li className="flow-step">
              <span className="flow-num">2</span>
              <div>
                <h4>The transport normalizes it</h4>
                <p>
                  The browser audio is already 16 kHz PCM16 (the Web Audio API resamples the mic for
                  free). Twilio&apos;s audio is decoded from μ-law and resampled 8 → 16 kHz. Either
                  way, <code>CallSession</code> receives the same 16 kHz PCM16 stream.
                </p>
              </div>
            </li>
            <li className="flow-step">
              <span className="flow-num">3</span>
              <div>
                <h4>Gemini Live streams back</h4>
                <p>Continuously, as the conversation runs: speech audio, live transcripts, or a tool call.</p>
              </div>
            </li>
            <li className="flow-step is-branch">
              <span className="flow-num">4</span>
              <div>
                <h4>On a tool call</h4>
                <p>
                  <code>CallSession</code> looks up the handler by name and runs it with the call&apos;s{" "}
                  <code>CallContext</code> — the same object <code>verify_customer</code> set
                  earlier. The handler never receives a customer ID from the model; it reads the
                  verified one from the context.
                </p>
              </div>
            </li>
            <li className="flow-step">
              <span className="flow-num">5</span>
              <div>
                <h4>The result goes back</h4>
                <p>Gemini continues speaking using whatever the handler returned — never a number it made up itself.</p>
              </div>
            </li>
            <li className="flow-step is-branch">
              <span className="flow-num">6</span>
              <div>
                <h4>If the caller talks over it</h4>
                <p>Gemini reports <code>interrupted</code>; the transport clears whatever audio was already queued for playback.</p>
              </div>
            </li>
            <li className="flow-step">
              <span className="flow-num">7</span>
              <div>
                <h4>Ending the call</h4>
                <p>
                  <code>escalate_to_agent</code> or <code>end_call</code> sets state on the context.{" "}
                  <code>CallSession</code> waits for the goodbye audio to actually finish playing,
                  then tells the transport to close — never mid-sentence.
                </p>
              </div>
            </li>
          </ol>
        </section>

        <section className="doc-section" id="transport">
          <p className="doc-kicker">03</p>
          <h2>The transport abstraction</h2>
          <p>
            Adding Twilio meant writing one new file — protocol framing, μ-law conversion, waiting
            for Twilio&apos;s <code>mark</code> echo before hanging up — and changing nothing in the
            agent, the tools, or the escalate/end-call state machine. Both transports satisfy the
            same five-method shape:
          </p>
          <div className="doc-code">
            <pre>{`class Transport(Protocol):
    async def receive_audio(self) -> bytes | None: ...
    async def send_audio(self, pcm24k: bytes) -> None: ...
    async def clear_playback(self) -> None: ...
    async def send_event(self, event: dict) -> None: ...
    async def finish(self) -> None: ...`}</pre>
          </div>
          <p>
            <strong>This paid off once already.</strong> The rule that a call must only end after
            its goodbye audio finishes — not on the network event that triggers it — lives entirely
            in <code>CallSession</code>. Fixed once, both the browser and the phone got it for free.
            The split was tested by swapping the transport under a fake WebSocket and confirming the
            browser call flows were unaffected, before a line of Twilio code existed.
          </p>
        </section>

        <section className="doc-section" id="audio">
          <p className="doc-kicker">04</p>
          <h2>Audio pipeline</h2>
          <p>
            Gemini Live takes <strong>16 kHz</strong> mono PCM16 in and returns{" "}
            <strong>24 kHz</strong> PCM16 out — two different rates, in two different directions.
            Phone networks add a third: <strong>8 kHz μ-law</strong>, a compressed 1-byte-per-sample
            format designed for voice-grade telephony, not for a neural model.
          </p>
          <p>
            The browser sidesteps most of this — asking for a 16 kHz <code>AudioContext</code> makes
            the browser resample the mic for you, and the returned audio is played at the 24 kHz
            rate it already arrives in. The Twilio transport does the real conversion: μ-law decode,
            then 8 → 16 kHz for Gemini; 24 → 8 kHz then μ-law encode for the caller.
          </p>
          <p>
            The resampler is <strong>stateful</strong> on purpose. Phone audio arrives as 20 ms
            frames, and resampling each frame in isolation — treating it as a standalone signal —
            produces audible clicks at every frame boundary. Carrying the filter state between calls
            to <code>audioop.ratecv</code> removes them.
          </p>
        </section>

        <section className="doc-section" id="security">
          <p className="doc-kicker">05</p>
          <h2>Security &amp; verification</h2>
          <p>
            <strong>Authorization lives in code, not in the prompt.</strong> A prompt can be talked
            around; a function can&apos;t. The verified customer ID is stored on a per-call{" "}
            <code>CallContext</code> that only <code>verify_customer</code> can set. Data tools take
            no customer ID from the model — they read it from the context — and the data layer
            refuses to return any record that belongs to someone else. Asking for another
            customer&apos;s loan, claiming to be a spouse, or saying &quot;ignore your
            instructions&quot; all end at code that has nothing to return.
          </p>
          <p>
            <strong>The model never decides when the call ends.</strong> Escalation and hang-up set
            state on the server; the server waits for the goodbye audio, tells the transport, and
            the transport lets it finish playing before closing.
          </p>
          <p>
            <strong>It can&apos;t claim actions it didn&apos;t take.</strong> Early testing surfaced
            a real failure: the model announced &quot;connecting you to a human agent&quot; when no
            tool existed yet to do that. The prompt now forbids describing any action before its
            tool has actually returned success, and escalation is honestly a callback, not a live
            transfer.
          </p>
        </section>

        <section className="doc-section" id="tools">
          <p className="doc-kicker">06</p>
          <h2>Tools</h2>
          <p>Five functions, each backed by mock loans-and-deposits data, described to Gemini as callable tools.</p>
          <table className="doc-table">
            <thead>
              <tr><th>Tool</th><th>Takes</th><th>Does</th></tr>
            </thead>
            <tbody>
              {TOOLS.map((t) => (
                <tr key={t.name}>
                  <td data-label="Tool"><code>{t.name}</code></td>
                  <td data-label="Takes">{t.input}</td>
                  <td data-label="Does">{t.does}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="doc-section" id="latency">
          <p className="doc-kicker">07</p>
          <h2>Latency</h2>
          <p>
            Time from the end of the caller&apos;s speech to the first byte of audio back, measured
            against the same speech clip, two runs each from a development machine — indicative, not
            a benchmark suite:
          </p>
          <div className="bar-chart">
            {LATENCY.map((l) => (
              <div className={`bar-row ${l.selected ? "is-selected" : ""}`} key={l.model}>
                <span className="bar-label">{l.model}</span>
                <span className="bar-track">
                  <span className="bar-fill" style={{ width: `${(l.seconds / MAX_LATENCY) * 100}%` }} />
                </span>
                <span className="bar-value">{l.seconds.toFixed(2)}s</span>
              </div>
            ))}
          </div>
          <p><code>gemini-3.8-live</code> is what the agent runs on — chosen by measurement, not by release date.</p>
        </section>

        <section className="doc-section" id="stack">
          <p className="doc-kicker">08</p>
          <h2>Stack</h2>
          <div className="stack-grid">
            <div className="stack-group">
              <h3>Backend</h3>
              <ul>
                <li>Python 3.12</li>
                <li>FastAPI + WebSockets</li>
                <li>google-genai (Gemini Live API)</li>
                <li>Twilio Media Streams</li>
                <li>pytest</li>
              </ul>
            </div>
            <div className="stack-group">
              <h3>Frontend</h3>
              <ul>
                <li>Next.js (App Router)</li>
                <li>TypeScript</li>
                <li>Web Audio API + AudioWorklet</li>
              </ul>
            </div>
            <div className="stack-group">
              <h3>Infra</h3>
              <ul>
                <li>nginx</li>
                <li>PM2</li>
                <li>Let&apos;s Encrypt / Certbot</li>
              </ul>
            </div>
          </div>
        </section>

        <Link href="/" className="doc-back">Back to the demo</Link>
      </main>
    </div>
  );
}
