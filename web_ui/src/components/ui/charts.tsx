import React from "react";

/* ------------------------------ Sparkline --------------------------------- */
export function Sparkline({
  data,
  color = "#818cf8",
  width = 96,
  height = 28,
  fill = true,
}: {
  data: number[];
  color?: string;
  width?: number;
  height?: number;
  fill?: boolean;
}) {
  const id = React.useId();
  if (!data.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1 || 1);
  const pts = data.map((d, i) => [i * step, height - ((d - min) / range) * (height - 4) - 2]);
  const line = pts.map((p, i) => `${i === 0 ? "M" : "L"} ${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(" ");
  const area = `${line} L ${width} ${height} L 0 ${height} Z`;
  return (
    <svg width={width} height={height} className="overflow-visible">
      <defs>
        <linearGradient id={`sp-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.35" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {fill && <path d={area} fill={`url(#sp-${id})`} />}
      <path d={line} fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="2" fill={color} />
    </svg>
  );
}

/* ------------------------------ AreaChart --------------------------------- */
export function AreaChart({
  data,
  color = "#818cf8",
  height = 200,
  showGrid = true,
}: {
  data: number[];
  color?: string;
  height?: number;
  showGrid?: boolean;
}) {
  const id = React.useId();
  const width = 720;
  const padL = 6;
  const padR = 6;
  const padT = 8;
  const padB = 8;
  const w = width - padL - padR;
  const h = height - padT - padB;
  if (!data.length) return null;
  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const step = w / (data.length - 1 || 1);
  const x = (i: number) => padL + i * step;
  const y = (v: number) => padT + h - ((v - min) / range) * h;
  const line = data.map((d, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(d).toFixed(1)}`).join(" ");
  const area = `${line} L ${x(data.length - 1).toFixed(1)} ${padT + h} L ${x(0).toFixed(1)} ${padT + h} Z`;
  const gridY = [0, 0.25, 0.5, 0.75, 1];
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" style={{ height }} preserveAspectRatio="none">
      <defs>
        <linearGradient id={`ar-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.42" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      {showGrid &&
        gridY.map((g, i) => (
          <line
            key={i}
            x1={padL}
            x2={width - padR}
            y1={padT + g * h}
            y2={padT + g * h}
            stroke="rgba(148,163,184,0.1)"
            strokeWidth="1"
            vectorEffect="non-scaling-stroke"
          />
        ))}
      <path d={area} fill={`url(#ar-${id})`} />
      <path
        d={line}
        fill="none"
        stroke={color}
        strokeWidth="2.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

/* -------------------------------- Donut ----------------------------------- */
export function Donut({
  value,
  size = 120,
  stroke = 12,
  color = "#818cf8",
  track = "rgba(148,163,184,0.12)",
  label,
  sublabel,
}: {
  value: number;
  size?: number;
  stroke?: number;
  color?: string;
  track?: string;
  label?: string;
  sublabel?: string;
}) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.max(0, Math.min(1, value)));
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={track} strokeWidth={stroke} />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset 0.8s cubic-bezier(0.16,1,0.3,1)" }}
        />
      </svg>
      <div className="absolute text-center">
        <div className="text-xl font-bold tabular text-white">{label}</div>
        {sublabel && <div className="text-[10px] font-medium uppercase tracking-wide text-slate-500">{sublabel}</div>}
      </div>
    </div>
  );
}

/* ------------------------------- Gauge 270° ------------------------------- */
function polar(cx: number, cy: number, r: number, deg: number) {
  const a = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}
function arc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const s = polar(cx, cy, r, startDeg);
  const e = polar(cx, cy, r, endDeg);
  const large = endDeg - startDeg <= 180 ? 0 : 1;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}

export function Gauge({
  value,
  size = 150,
  stroke = 12,
  color = "#34d399",
}: {
  value: number;
  size?: number;
  stroke?: number;
  color?: string;
}) {
  const start = 225;
  const sweep = 270;
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const f = Math.max(0, Math.min(1, value));
  const valEnd = start + sweep * f;
  return (
    <svg width={size} height={size}>
      <path d={arc(cx, cy, r, start, start + sweep)} fill="none" stroke="rgba(148,163,184,0.14)" strokeWidth={stroke} strokeLinecap="round" />
      <path
        d={arc(cx, cy, r, start, valEnd)}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeLinecap="round"
        style={{ transition: "all 0.8s cubic-bezier(0.16,1,0.3,1)" }}
      />
    </svg>
  );
}

/* --------------------------------- Bars ----------------------------------- */
export function Bars({
  data,
  color = "#818cf8",
  height = 60,
}: {
  data: number[];
  color?: string;
  height?: number;
}) {
  const max = Math.max(...data, 1);
  return (
    <div className="flex items-end gap-[3px]" style={{ height }}>
      {data.map((d, i) => (
        <div
          key={i}
          className="grow-bar flex-1 rounded-sm"
          style={{
            height: `${(d / max) * 100}%`,
            background: `linear-gradient(180deg, ${color}, ${color}55)`,
            animationDelay: `${i * 24}ms`,
            minHeight: 2,
          }}
          title={String(d)}
        />
      ))}
    </div>
  );
}
