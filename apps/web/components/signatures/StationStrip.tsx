/* ALMANAC's signature: the station strip.
 *
 * A meteorological station model is a fixed notation — temperature at upper
 * left, a barb showing wind speed and direction, present weather at lower
 * left — that a forecaster reads at a glance without reading any words. This
 * is that notation, carrying SIDRA's variables instead of a synoptic chart's:
 * forecast temperature, wind, the Hijri date, and the demand index with its
 * prediction interval drawn as a bracket rather than printed as a number.
 *
 * It appears on every page. The claim it makes is that a promo planner should
 * be able to read the day's conditions the way a forecaster reads a chart.
 */

import type { Zone } from "@/lib/demo";

export function StationStrip({ zone, hijri }: { zone: Zone; hijri: string }) {
  // The bracket's width encodes the interval. A wide bracket is an uncertain
  // forecast and looks like one, which is the whole point.
  const bracket = Math.min(48, Math.max(6, zone.pi * 160));

  return (
    <div
      className="row between"
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "0.72rem",
        letterSpacing: "0.06em",
        padding: "0.5rem 0",
        borderBottom: "1px solid var(--rule)",
        color: "var(--text-muted)",
      }}
    >
      <div className="row" style={{ gap: "1.1rem" }}>
        <svg width="46" height="30" viewBox="0 0 46 30" aria-hidden="true">
          {/* station circle: filled fraction is cloud cover, here always clear */}
          <circle cx="23" cy="15" r="5.5" fill="none" stroke="var(--text-faint)" strokeWidth="1.2" />
          {/* wind barb, pointing into the wind, with one full barb per 10 km/h */}
          <line x1="28.5" y1="15" x2="42" y2="8" stroke="var(--text-muted)" strokeWidth="1.2" />
          <line x1="42" y1="8" x2="38" y2="4" stroke="var(--text-muted)" strokeWidth="1.2" />
          <line x1="37" y1="10.5" x2="33.5" y2="7" stroke="var(--text-muted)" strokeWidth="1.2" />
          <text x="0" y="9" fontSize="8" fill="var(--heat-5)" fontFamily="var(--font-mono)">
            {zone.tempC}
          </text>
          <text x="0" y="27" fontSize="8" fill="var(--text-faint)" fontFamily="var(--font-mono)">
            RH38
          </text>
        </svg>

        <span aria-hidden="true" style={{ color: "var(--rule)" }}>│</span>

        <span>
          <span style={{ color: "var(--text-faint)" }}>ZONE </span>
          <span style={{ color: "var(--text)" }}>{zone.code}</span>
        </span>

        <span>
          <span style={{ color: "var(--text-faint)" }}>HIJRI </span>
          {hijri}
        </span>
      </div>

      <div className="row" style={{ gap: "0.6rem" }}>
        <span style={{ color: "var(--text-faint)" }}>DEMAND IDX</span>
        <span style={{ color: "var(--text)", fontSize: "0.86rem" }}>{zone.index.toFixed(2)}</span>
        {/* The interval bracket. Drawn, not printed — a number invites you to
            read it as precision, a bracket shows you the width. */}
        <svg width={bracket} height="12" viewBox={`0 0 ${bracket} 12`} role="img"
             aria-label={`80% prediction interval, plus or minus ${zone.pi.toFixed(2)}`}>
          <line x1="1" y1="2" x2="1" y2="10" stroke="var(--text-faint)" strokeWidth="1.2" />
          <line x1={bracket - 1} y1="2" x2={bracket - 1} y2="10" stroke="var(--text-faint)" strokeWidth="1.2" />
          <line x1="1" y1="6" x2={bracket - 1} y2="6" stroke="var(--text-faint)" strokeWidth="1.2" />
        </svg>
        <span style={{ color: "var(--text-faint)" }}>±{zone.pi.toFixed(2)}</span>
      </div>
    </div>
  );
}
