"use client";

/* The fallback, and it is not a consolation prize.
 *
 * WebGL is absent on more machines than people expect — an old browser, a
 * locked-down laptop, a headless crawler, a reader who has turned it off. This
 * shows the same four lanes, the same fifty-six days, the same event bands and
 * the same intervals, in SVG. It is genuinely readable, and on a phone it is
 * arguably the better view.
 *
 * The interval is drawn as a lighter extension above each bar rather than as a
 * cap on a box, because in two dimensions a cap has nowhere to sit.
 */

import type { TerrainResponse } from "@/lib/api";

const LANE_ORDER = ["DXB-MAR", "DXB-DTN", "DXB-MOE", "DXB-DEI"];

export function TerrainSVG({ data, focusDay }: { data: TerrainResponse; focusDay: number }) {
  const lanes = LANE_ORDER.map((z) => data.lanes.find((l) => l.zone === z)).filter(
    Boolean,
  ) as TerrainResponse["lanes"];
  const days = Math.min(data.days, data.horizon.length);
  const peak = Math.max(...lanes.flatMap((l) => l.days.map((d) => d.hi)), 1);

  const W = 900;
  const LANE_H = 62;
  const H = lanes.length * LANE_H + 46;
  const x = (i: number) => (i / Math.max(days - 1, 1)) * (W - 70) + 58;
  const bw = (W - 70) / days;

  return (
    <figure style={{ margin: 0 }}>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        width="100%"
        role="img"
        aria-label={`Forecast demand for ${lanes.length} sites over ${days} days, with event bands and prediction intervals`}
        style={{ display: "block" }}
      >
        {/* event bands, behind everything */}
        {data.bands.slice(0, 10).map((b) => {
          const s = data.horizon.indexOf(b.start);
          const e = data.horizon.indexOf(b.end);
          if (s < 0 && e < 0) return null;
          const from = s < 0 ? 0 : s;
          const to = e < 0 ? days - 1 : e;
          return (
            <g key={b.event_id}>
              <rect
                x={x(from) - bw / 2}
                y={4}
                width={Math.max(bw, x(to) - x(from) + bw)}
                height={lanes.length * LANE_H}
                fill="var(--accent)"
                opacity={0.05 + b.weight * 0.05}
              />
              <title>{`${b.title} · ${b.start} to ${b.end}`}</title>
            </g>
          );
        })}

        {lanes.map((lane, li) => {
          const base = (li + 1) * LANE_H;
          return (
            <g key={lane.zone}>
              <text x={4} y={base - LANE_H / 2 + 4} fontSize="9" fontFamily="var(--font-mono)"
                    fill="var(--text-faint)">
                {lane.zone}
              </text>
              <line x1={58} x2={W - 12} y1={base} y2={base} stroke="var(--border)" />
              {lane.days.slice(0, days).map((d, i) => {
                const h = (d.yhat / peak) * (LANE_H - 12);
                const hi = (d.hi / peak) * (LANE_H - 12);
                const lo = (d.lo / peak) * (LANE_H - 12);
                return (
                  <g key={d.date}>
                    {/* the interval, drawn first so the point estimate sits on it */}
                    <rect
                      x={x(i) - bw * 0.42}
                      y={base - hi}
                      width={bw * 0.84}
                      height={Math.max(1, hi - lo)}
                      fill="var(--sig-actual)"
                      opacity={0.28}
                    />
                    <rect
                      x={x(i) - bw * 0.34}
                      y={base - h}
                      width={bw * 0.68}
                      height={Math.max(1, h)}
                      fill="var(--sig-forecast)"
                      opacity={i === focusDay ? 1 : 0.85}
                    />
                    <title>{`${lane.name} · ${d.date} · ${Math.round(d.yhat)} (${Math.round(d.lo)}–${Math.round(d.hi)})`}</title>
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* the weather ribbon along the bottom */}
        {data.ribbon.slice(0, days).map((r, i) => {
          const t = Math.min(1, Math.max(0, (r.apparent_c - 24) / 20));
          return (
            <rect
              key={r.date}
              x={x(i) - bw / 2}
              y={lanes.length * LANE_H + 8}
              width={bw}
              height={9}
              fill={`hsl(${Math.round(223 - t * 223)} 58% 52%)`}
            >
              <title>{`${r.date} · ${r.apparent_c}°C apparent, evening`}</title>
            </rect>
          );
        })}

        {data.horizon
          .slice(0, days)
          .map((d, i) => ({ d, i }))
          .filter(({ i }) => i % Math.ceil(days / 7) === 0)
          .map(({ d, i }) => (
            <text key={d} x={x(i)} y={H - 6} fontSize="8.5" textAnchor="middle"
                  fontFamily="var(--font-mono)" fill="var(--text-faint)">
              {d.slice(5)}
            </text>
          ))}
      </svg>
      <figcaption className="faint" style={{ marginTop: "0.4rem" }}>
        Four sites, {days} days. The lighter extension above each bar is the 80% prediction
        interval; the strip below is evening apparent temperature. Event bands cross every lane.
      </figcaption>
    </figure>
  );
}
