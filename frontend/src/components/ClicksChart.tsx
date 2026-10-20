import { useState } from "react";
import type { DailyClicks } from "../services";

/** Daily clicks as columns, unique visitors as a line over them. Plain SVG, no chart library. */
export default function ClicksChart({ daily }: { daily: DailyClicks[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const width = 720;
  const height = 220;
  const pad = { top: 16, right: 12, bottom: 28, left: 36 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;

  const max = Math.max(1, ...daily.map((d) => d.clicks));
  const niceMax = max <= 5 ? max : Math.ceil(max / 5) * 5;
  const step = innerW / Math.max(1, daily.length);
  const barW = Math.max(2, step * 0.7);
  const y = (v: number) => pad.top + innerH - (v / niceMax) * innerH;
  const ticks = [0, niceMax / 2, niceMax].map((t) => Math.round(t));

  const line = daily
    .map((d, i) => `${i === 0 ? "M" : "L"}${pad.left + i * step + step / 2},${y(d.unique_visitors)}`)
    .join(" ");
  const active = hover === null ? null : daily[hover];
  const label = (iso: string) =>
    new Date(`${iso}T00:00:00Z`).toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });

  return (
    <figure className="chart">
      <div className="chart-legend small">
        <span className="legend-item">
          <span className="swatch swatch-bar" /> Clicks
        </span>
        <span className="legend-item">
          <span className="swatch swatch-line" /> Unique visitors
        </span>
        <span className="chart-readout muted">
          {active ? `${label(active.date)}: ${active.clicks} clicks, ${active.unique_visitors} unique` : " "}
        </span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Clicks per day" onMouseLeave={() => setHover(null)}>
        {ticks.map((t) => (
          <g key={t}>
            <line className="grid" x1={pad.left} x2={width - pad.right} y1={y(t)} y2={y(t)} />
            <text className="axis" x={pad.left - 6} y={y(t) + 4} textAnchor="end">
              {t}
            </text>
          </g>
        ))}
        {daily.map((d, i) => {
          const x = pad.left + i * step + (step - barW) / 2;
          return (
            <g key={d.date} onMouseEnter={() => setHover(i)}>
              <rect className="hit" x={pad.left + i * step} y={pad.top} width={step} height={innerH} />
              <rect
                className={hover === i ? "bar bar-active" : "bar"}
                x={x}
                y={y(d.clicks)}
                width={barW}
                height={Math.max(0, pad.top + innerH - y(d.clicks))}
                rx={2}
              />
            </g>
          );
        })}
        <path className="visitors" d={line} fill="none" />
        {[0, Math.floor((daily.length - 1) / 2), daily.length - 1]
          .filter((i, idx, arr) => daily[i] && arr.indexOf(i) === idx)
          .map((i) => (
            <text
              key={i}
              className="axis"
              x={pad.left + i * step + step / 2}
              y={height - 8}
              textAnchor={i === 0 ? "start" : i === daily.length - 1 ? "end" : "middle"}
            >
              {label(daily[i].date)}
            </text>
          ))}
      </svg>
    </figure>
  );
}
