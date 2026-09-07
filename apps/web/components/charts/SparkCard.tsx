"use client";

/* One site, one card, one shared scale.
 *
 * ALMANAC shows the four sites as small multiples rather than as four coloured
 * lines on one axis. The shared `scaleMax` is what makes it a comparison: with
 * per-card scaling every site looks equally busy, which is the most common way
 * a small-multiple grid lies.
 */

import { fmt } from "@/components/charts/Chart";

export type Spark = {
  code: string;
  name: string;
  points: number[];
  /** Optional 80% interval, as [lo, hi] per point. */
  band?: [number, number][];
  index?: number;
  /** A short label shown where the index would be, for cards whose headline
   *  number is not a demand index. */
  badge?: string;
  pi?: number;
  detail?: string;
  tempC?: number;
};

export function SparkCard({
  spark,
  scaleMax,
  height = 46,
}: {
  spark: Spark;
  scaleMax: number;
  height?: number;
}) {
  const w = 220;
  const n = spark.points.length;
  const x = (i: number) => (i / Math.max(n - 1, 1)) * w;
  const y = (v: number) => height - (v / (scaleMax || 1)) * (height - 3) - 1.5;

  const line = spark.points.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const band =
    spark.band &&
    [
      ...spark.band.map((b, i) => `${x(i).toFixed(1)},${y(b[1]).toFixed(1)}`),
      ...[...spark.band].reverse().map((b, i) => `${x(n - 1 - i).toFixed(1)},${y(b[0]).toFixed(1)}`),
    ].join(" ");

  return (
    <article className="card stack" style={{ gap: "0.5rem", minWidth: 0 }}>
      <div className="between">
        <span className="code">{spark.code}</span>
        {spark.index !== undefined && (
          <span className="num" style={{ fontSize: "var(--step-1)" }}>
            {spark.index.toFixed(2)}×
          </span>
        )}
        {spark.index === undefined && spark.badge && (
          <span className="chip">{spark.badge}</span>
        )}
      </div>
      <div>
        <div className="h3">{spark.name}</div>
        {spark.detail && <div className="faint">{spark.detail}</div>}
      </div>

      <svg
        viewBox={`0 0 ${w} ${height}`}
        width="100%"
        height={height}
        role="img"
        aria-label={`${spark.name}: ${n} points, peak ${fmt(Math.max(...spark.points))}`}
        style={{ display: "block", overflow: "visible" }}
      >
        {band && <polygon points={band} fill="var(--sig-forecast)" opacity="0.16" />}
        <path d={line} fill="none" stroke="var(--sig-forecast)" strokeWidth="1.6"
              strokeLinejoin="round" strokeLinecap="round" />
      </svg>

      <div className="between faint">
        <span>{spark.pi !== undefined ? `±${spark.pi.toFixed(2)} at 80%` : `peak ${fmt(Math.max(...spark.points))}`}</span>
        {spark.tempC !== undefined && <span className="num">{Math.round(spark.tempC)}°C</span>}
      </div>
    </article>
  );
}

/** The grid, with one scale computed across every card in it. */
export function SparkGrid({ sparks, caption }: { sparks: Spark[]; caption?: string }) {
  const scaleMax = Math.max(
    ...sparks.flatMap((s) => [...s.points, ...(s.band?.map((b) => b[1]) ?? [])]),
    1,
  );
  return (
    <div className="stack">
      <div className="cards">
        {sparks.map((s) => (
          <SparkCard key={s.code} spark={s} scaleMax={scaleMax} />
        ))}
      </div>
      {caption && (
        <p className="faint" style={{ margin: 0 }}>
          {caption} · all four drawn to one scale, so the cards are read against each other
        </p>
      )}
    </div>
  );
}
