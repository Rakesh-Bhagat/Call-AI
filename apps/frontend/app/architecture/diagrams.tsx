function Box({ x, y, w, h, label, variant }: { x: number; y: number; w: number; h: number; label: string; variant?: "brass" | "slate" }) {
  const cls = variant === "brass" ? "n-box-brass" : variant === "slate" ? "n-box-slate" : "n-box";
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx={8} className={cls} />
      <text x={x + w / 2} y={y + h / 2} textAnchor="middle" dominantBaseline="middle" className="n-label" fontSize={13}>
        {label}
      </text>
    </g>
  );
}

function Edge({ x1, y1, x2, y2, label, twoWay = true }: { x1: number; y1: number; x2: number; y2: number; label: string; twoWay?: boolean }) {
  return (
    <g>
      <line
        x1={x1} y1={y1} x2={x2} y2={y2}
        className="edge"
        markerEnd="url(#arrow)"
        markerStart={twoWay ? "url(#arrow)" : undefined}
      />
      <text x={(x1 + x2) / 2} y={Math.min(y1, y2) - 10} textAnchor="middle" className="edge-label">
        {label}
      </text>
    </g>
  );
}

export function OverviewDiagram() {
  return (
    <svg viewBox="0 0 700 260" className="diagram" role="img" aria-label="Caller connects through a Transport to CallSession, which streams to Gemini Live and calls tools.">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0,0 L10,5 L0,10 z" className="edge-arrow" />
        </marker>
      </defs>

      <Edge x1={160} y1={70} x2={193} y2={70} label="audio" />
      <Edge x1={333} y1={70} x2={366} y2={70} label="16 kHz PCM" />
      <Edge x1={506} y1={70} x2={539} y2={70} label="audio + tool calls" />
      <Edge x1={436} y1={100} x2={436} y2={170} label="" />

      <Box x={20} y={40} w={140} h={60} label="Caller" />
      <Box x={193} y={40} w={140} h={60} label="Transport" variant="slate" />
      <Box x={366} y={40} w={140} h={60} label="CallSession" />
      <Box x={539} y={40} w={140} h={60} label="Gemini Live" variant="brass" />
      <Box x={366} y={170} w={140} h={60} label="Tools + Data" variant="slate" />

      <text x={456} y={140} className="edge-label">tool_call / result</text>
    </svg>
  );
}
