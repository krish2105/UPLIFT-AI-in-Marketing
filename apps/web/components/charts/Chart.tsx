"use client";

/* The chart primitives.
 *
 * No charting library. Every mark reads a design token, so a chart is correct
 * in both registers by construction rather than by a second theme configuration
 * that can drift from the first. The palette these draw from is measured by
 * apps/web/scripts/check-palette.mjs.
 *
 * Rules applied throughout, from the dataviz reference:
 *   · one y-axis, ever — two measures of different scale get two charts
 *   · thin marks, recessive grid, selective direct labels, never a number on
 *     every point
 *   · a legend whenever there is more than one series, and identity is never
 *     carried by colour alone: the legend swatch is paired with its name
 *   · text wears text tokens, never the series colour
 *   · every chart has a hover layer, because an SVG chart IS interactive
 *   · a data table behind every chart, so the numbers are reachable without
 *     reading pixels
 */

import { useId, useMemo, useState } from "react";

/* ALMANAC HAS NO PER-SITE COLOUR, DELIBERATELY.
 *
 * Colour means temperature here. Giving four sites four hues would spend the
 * palette on identity and leave nothing to say "hot" with, and would need four
 * colours that survive a colour-vision check. Sites are drawn as SMALL
 * MULTIPLES instead — one card each, one shared scale, one forecast blue — so
 * identity comes from position and label. apps/web/scripts/check-palette.mjs
 * fails if a --zone-* token ever appears.
 *
 * It is also the better comparison. Four sparklines on a shared scale are read
 * against each other; four overlaid lines are read against whichever is on top.
 *
 * Dayparts keep a ramp position rather than a hue: morning is the cool end of
 * the thermal ramp and evening the warm end, which is both true and consistent
 * with the one rule.
 */
export const DAYPART_TOKEN: Record<string, string> = {
  morning: "--heat-1",
  midday: "--heat-3",
  evening: "--heat-5",
};

export function fmt(n: number): string {
  if (n >= 10000) return `${(n / 1000).toFixed(1)}k`;
  return Math.round(n).toLocaleString("en-GB");
}

/** Round tick values a reader can hold in their head.
 *
 * Dividing an arbitrary maximum into five gives labels like 251.856, which is
 * precision nobody asked for and nobody can compare across charts. This snaps
 * the step to 1, 2 or 5 times a power of ten and returns whole ticks.
 */
export function niceTicks(max: number, count = 5): number[] {
  if (!(max > 0)) return [0];
  const raw = max / count;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const out: number[] = [];
  for (let v = 0; v <= max + step * 0.001; v += step) out.push(Math.round(v * 1000) / 1000);
  return out;
}

/* ── the frame ────────────────────────────────────────────────────────────── */

type Frame = { w: number; h: number; pad: { t: number; r: number; b: number; l: number } };
const FRAME: Frame = { w: 720, h: 260, pad: { t: 14, r: 14, b: 26, l: 44 } };

function scale(domain: [number, number], range: [number, number]) {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  return (v: number) => r0 + ((v - d0) / span) * (r1 - r0);
}

/* ── line series with a prediction interval ───────────────────────────────── */

export type Series = { key: string; label: string; token: string; points: { x: number; y: number }[] };

export function LineChart({
  series,
  caption,
  yLabel,
  band,
  bandPoints,
  xTicks,
  height = FRAME.h,
}: {
  series: Series[];
  caption: string;
  yLabel: string;
  /** Optional symmetric interval as a fraction of y, drawn behind the lines. */
  band?: number;
  /** An explicit [lo, hi] per point — what a quantile model actually produces.
   *  Takes precedence over `band`, which only exists for illustrative bands. */
  bandPoints?: [number, number][];
  xTicks?: { at: number; label: string }[];
  height?: number;
}) {
  const id = useId();
  const [hover, setHover] = useState<number | null>(null);
  const [showTable, setShowTable] = useState(false);

  const { w, pad } = FRAME;
  const h = height;
  const xs = series.flatMap((s) => s.points.map((p) => p.x));
  const ys = series.flatMap((s) => s.points.map((p) => p.y));
  const yMax = Math.max(...ys, ...(bandPoints?.map((b) => b[1]) ?? []), 1) * 1.08;
  const x = scale([Math.min(...xs), Math.max(...xs)], [pad.l, w - pad.r]);
  const y = scale([0, yMax], [h - pad.b, pad.t]);

  const ticks = useMemo(() => niceTicks(yMax), [yMax]);

  const nearest = hover === null ? null : hover;

  return (
    <figure className="chart" style={{ margin: 0 }}>
      <svg
        viewBox={`0 0 ${w} ${h}`}
        width="100%"
        role="img"
        aria-label={caption}
        style={{ display: "block", overflow: "visible", touchAction: "pan-y" }}
        onMouseLeave={() => setHover(null)}
        onMouseMove={(e) => {
          const box = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
          const px = ((e.clientX - box.left) / box.width) * w;
          const i = Math.round(
            ((px - pad.l) / (w - pad.l - pad.r)) * (series[0].points.length - 1),
          );
          setHover(Math.max(0, Math.min(series[0].points.length - 1, i)));
        }}
      >
        {/* grid, recessive */}
        {ticks.map((v) => (
          <g key={v}>
            <line x1={pad.l} x2={w - pad.r} y1={y(v)} y2={y(v)} stroke="var(--border)" strokeWidth="1" />
            <text x={pad.l - 6} y={y(v) + 3.5} textAnchor="end" fontSize="9"
                  fontFamily="var(--font-mono)" fill="var(--text-faint)">
              {fmt(v)}
            </text>
          </g>
        ))}

        {xTicks?.map((tk) => (
          <text key={tk.at} x={x(tk.at)} y={h - pad.b + 15} textAnchor="middle" fontSize="9"
                fontFamily="var(--font-mono)" fill="var(--text-faint)">
            {tk.label}
          </text>
        ))}

        {/* the interval band, behind everything */}
        {bandPoints && (
          <polygon
            fill="var(--sig-forecast)"
            opacity="0.18"
            points={[
              ...bandPoints.map((b, i) => `${x(series[0].points[i].x)},${y(b[1])}`),
              ...[...bandPoints].reverse().map((b, i) =>
                `${x(series[0].points[bandPoints.length - 1 - i].x)},${y(b[0])}`),
            ].join(" ")}
          />
        )}
        {bandPoints === undefined && band !== undefined &&
          series.map((s) => (
            <polygon
              key={`${id}-${s.key}-band`}
              fill={`var(${s.token})`}
              opacity="0.14"
              points={[
                ...s.points.map((p) => `${x(p.x)},${y(p.y * (1 + band))}`),
                ...[...s.points].reverse().map((p) => `${x(p.x)},${y(Math.max(0, p.y * (1 - band)))}`),
              ].join(" ")}
            />
          ))}

        {series.map((s) => (
          <path
            key={s.key}
            d={s.points.map((p, i) => `${i ? "L" : "M"}${x(p.x).toFixed(1)},${y(p.y).toFixed(1)}`).join(" ")}
            fill="none"
            stroke={`var(${s.token})`}
            strokeWidth="2"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}

        {/* crosshair */}
        {nearest !== null && series[0].points[nearest] && (
          <>
            <line
              x1={x(series[0].points[nearest].x)} x2={x(series[0].points[nearest].x)}
              y1={pad.t} y2={h - pad.b} stroke="var(--border-strong)" strokeWidth="1" strokeDasharray="3 3"
            />
            {series.map((s) =>
              s.points[nearest] ? (
                <circle key={s.key} cx={x(s.points[nearest].x)} cy={y(s.points[nearest].y)} r="4"
                        fill={`var(${s.token})`} stroke="var(--bg)" strokeWidth="2" />
              ) : null,
            )}
          </>
        )}
      </svg>

      <figcaption className="stack" style={{ gap: "0.4rem", marginTop: "0.5rem" }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <div className="row" style={{ gap: "0.9rem" }}>
            {series.map((s) => (
              <span key={s.key} className="row" style={{ gap: "0.35rem" }}>
                <i aria-hidden="true" style={{
                  width: 10, height: 10, borderRadius: 2, background: `var(${s.token})`,
                  display: "inline-block",
                }} />
                <span className="faint">{s.label}</span>
                {nearest !== null && s.points[nearest] && (
                  <span className="num" style={{ fontSize: "var(--step--1)", color: "var(--text)" }}>
                    {fmt(s.points[nearest].y)}
                  </span>
                )}
              </span>
            ))}
          </div>
          <button type="button" className="btn" style={{ padding: "0.2rem 0.5rem", fontSize: "0.68rem" }}
                  aria-expanded={showTable} onClick={() => setShowTable((v) => !v)}>
            {showTable ? "Hide table" : "Table"}
          </button>
        </div>
        <span className="faint">{caption} · {yLabel}</span>
      </figcaption>

      {showTable && (
        <div className="scroll-x" style={{ marginTop: "0.6rem" }}>
          <table className="data">
            <thead>
              <tr>
                <th>x</th>
                {series.map((s) => <th key={s.key}>{s.label}</th>)}
              </tr>
            </thead>
            <tbody>
              {series[0].points.map((p, i) => (
                <tr key={i}>
                  <td className="num">{xTicks?.find((t) => t.at === p.x)?.label ?? p.x}</td>
                  {series.map((s) => <td key={s.key} className="num">{s.points[i]?.y ?? "—"}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </figure>
  );
}

/* ── grouped bars ─────────────────────────────────────────────────────────── */

export function GroupedBars({
  groups,
  categories,
  caption,
}: {
  groups: { key: string; label: string; values: Record<string, number> }[];
  categories: { key: string; label: string; token: string }[];
  caption: string;
}) {
  const [hover, setHover] = useState<string | null>(null);
  const max = Math.max(...groups.flatMap((g) => categories.map((c) => g.values[c.key] ?? 0)), 1);

  return (
    <figure style={{ margin: 0 }}>
      <div className="stack" style={{ gap: "0.8rem" }} role="img" aria-label={caption}>
        {groups.map((g) => (
          <div key={g.key} className="stack" style={{ gap: "0.3rem" }}>
            <div className="between">
              <span className="code">{g.label}</span>
              <span className="faint num">
                {fmt(categories.reduce((a, c) => a + (g.values[c.key] ?? 0), 0))}
              </span>
            </div>
            {/* 2px gaps between segments so adjacent fills never touch */}
            <div style={{ display: "flex", gap: 2, height: 22 }}>
              {categories.map((c) => {
                const v = g.values[c.key] ?? 0;
                const key = `${g.key}:${c.key}`;
                return (
                  <div
                    key={c.key}
                    title={`${g.label} · ${c.label}: ${v.toLocaleString("en-GB")}`}
                    onMouseEnter={() => setHover(key)}
                    onMouseLeave={() => setHover(null)}
                    style={{
                      width: `${(v / max) * 100}%`,
                      background: `var(${c.token})`,
                      borderRadius: 4,
                      opacity: hover && hover !== key ? 0.45 : 1,
                      transition: "opacity 120ms ease",
                      minWidth: v > 0 ? 3 : 0,
                    }}
                  />
                );
              })}
            </div>
          </div>
        ))}
      </div>
      <figcaption className="stack" style={{ gap: "0.4rem", marginTop: "0.7rem" }}>
        <div className="row" style={{ gap: "0.9rem" }}>
          {categories.map((c) => (
            <span key={c.key} className="row" style={{ gap: "0.35rem" }}>
              <i aria-hidden="true" style={{
                width: 10, height: 10, borderRadius: 2, background: `var(${c.token})`, display: "inline-block",
              }} />
              <span className="faint">{c.label}</span>
            </span>
          ))}
        </div>
        <span className="faint">{caption}</span>
      </figcaption>
    </figure>
  );
}

/* ── binned response ──────────────────────────────────────────────────────── */

export function ResponseChart({
  series,
  caption,
  xLabel,
  yLabel,
}: {
  series: { key: string; label: string; token: string; points: { x: number; y: number }[] }[];
  caption: string;
  xLabel: string;
  yLabel: string;
}) {
  const { w, pad } = FRAME;
  const h = 240;
  const xs = series.flatMap((s) => s.points.map((p) => p.x));
  const ys = series.flatMap((s) => s.points.map((p) => p.y));
  const yTop = Math.max(...ys) * 1.08;
  const x = scale([Math.min(...xs), Math.max(...xs)], [pad.l, w - pad.r]);
  const y = scale([0, yTop], [h - pad.b, pad.t]);
  const ticks = niceTicks(yTop);

  return (
    <figure style={{ margin: 0 }}>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label={caption}
           style={{ display: "block", overflow: "visible" }}>
        {ticks.map((v) => {
          return (
            <g key={v}>
              <line x1={pad.l} x2={w - pad.r} y1={y(v)} y2={y(v)} stroke="var(--border)" />
              <text x={pad.l - 6} y={y(v) + 3.5} textAnchor="end" fontSize="9"
                    fontFamily="var(--font-mono)" fill="var(--text-faint)">{fmt(v)}</text>
            </g>
          );
        })}
        {[...new Set(xs)].filter((_, i) => i % 3 === 0).map((v) => (
          <text key={v} x={x(v)} y={h - pad.b + 15} textAnchor="middle" fontSize="9"
                fontFamily="var(--font-mono)" fill="var(--text-faint)">{v}°</text>
        ))}
        {series.map((s) => (
          <g key={s.key}>
            <path
              d={s.points.map((p, i) => `${i ? "L" : "M"}${x(p.x).toFixed(1)},${y(p.y).toFixed(1)}`).join(" ")}
              fill="none" stroke={`var(${s.token})`} strokeWidth="2" strokeLinejoin="round" />
            {s.points.map((p) => (
              <circle key={p.x} cx={x(p.x)} cy={y(p.y)} r="3.5" fill={`var(${s.token})`}
                      stroke="var(--bg)" strokeWidth="1.5">
                <title>{`${s.label} · ${p.x}°C · ${Math.round(p.y)} visitors/hour`}</title>
              </circle>
            ))}
          </g>
        ))}
      </svg>
      <figcaption className="stack" style={{ gap: "0.4rem", marginTop: "0.5rem" }}>
        <div className="row" style={{ gap: "0.9rem" }}>
          {series.map((s) => (
            <span key={s.key} className="row" style={{ gap: "0.35rem" }}>
              <i aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 2,
                 background: `var(${s.token})`, display: "inline-block" }} />
              <span className="faint">{s.label}</span>
            </span>
          ))}
        </div>
        <span className="faint">{caption} · x: {xLabel} · y: {yLabel}</span>
      </figcaption>
    </figure>
  );
}

/* ── a single number, when a chart would be worse ─────────────────────────── */

export function StatTile({
  value,
  label,
  detail,
  token,
}: {
  value: string;
  label: string;
  detail?: string;
  token?: string;
}) {
  return (
    <div className="card stack" style={{ gap: "0.25rem" }}>
      <span className="eyebrow" style={{ margin: 0 }}>{label}</span>
      <span className="num" style={{
        fontSize: "var(--step-2)", lineHeight: 1.05,
        color: token ? `var(${token})` : "var(--text)",
      }}>
        {value}
      </span>
      {detail && <span className="faint">{detail}</span>}
    </div>
  );
}
