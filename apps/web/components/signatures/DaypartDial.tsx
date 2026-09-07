/* DAYPART's signature: the 24-hour dial.
 *
 * The dial is a clock face carrying one day of forecast demand for the active
 * zone. SIDRA's demand is bimodal, so the shape that appears is two lobes —
 * a commuter peak before 11:00 and a longer evening peak after 17:00 — and
 * the gap between them is the midday trough that makes a café's promo
 * calendar hard.
 *
 * It is not a decorative gauge: the three arcs ARE the media allocator's
 * daypart cells, coloured by the same tokens the allocator uses, and in the
 * application each is a control that scopes every other tab to that daypart.
 * Here it renders read-only.
 */

const DAYPARTS = [
  { from: 7, to: 11, token: "--dp-morning", name: "morning" },
  { from: 11, to: 17, token: "--dp-midday", name: "midday" },
  { from: 17, to: 23, token: "--dp-evening", name: "evening" },
] as const;

function tokenForHour(h: number) {
  return DAYPARTS.find((d) => h >= d.from && h < d.to)?.token ?? "--text-faint";
}

export function DaypartDial({ shape, size = 210 }: { shape: number[]; size?: number }) {
  const cx = size / 2;
  const cy = size / 2;
  const rInner = size * 0.26;
  const rOuter = size * 0.46;

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      role="img"
      aria-label="Forecast demand across 24 hours, showing a morning peak and a larger evening peak"
      style={{ display: "block" }}
    >
      {/* the dial face */}
      <circle cx={cx} cy={cy} r={rOuter} fill="none" stroke="var(--border)" strokeWidth="1" />
      <circle cx={cx} cy={cy} r={rInner} fill="none" stroke="var(--border)" strokeWidth="1" />

      {shape.map((v, h) => {
        // Midnight at the top, clockwise, so the dial reads like a clock.
        const a0 = (h / 24) * Math.PI * 2 - Math.PI / 2;
        const a1 = ((h + 0.86) / 24) * Math.PI * 2 - Math.PI / 2;
        const r = rInner + (rOuter - rInner) * v;
        const p = (ang: number, rad: number) => `${cx + Math.cos(ang) * rad},${cy + Math.sin(ang) * rad}`;
        return (
          <path
            key={h}
            d={`M ${p(a0, rInner)} L ${p(a0, r)} A ${r} ${r} 0 0 1 ${p(a1, r)} L ${p(a1, rInner)} Z`}
            fill={`var(${tokenForHour(h)})`}
            opacity={0.35 + v * 0.65}
          />
        );
      })}

      {/* 06 / 12 / 18 / 00 ticks — the only labels the dial needs */}
      {[0, 6, 12, 18].map((h) => {
        const a = (h / 24) * Math.PI * 2 - Math.PI / 2;
        return (
          <text
            key={h}
            x={cx + Math.cos(a) * (rOuter + 11)}
            y={cy + Math.sin(a) * (rOuter + 11) + 3.5}
            textAnchor="middle"
            fontSize="9"
            fontFamily="var(--font-mono)"
            fill="var(--text-faint)"
          >
            {String(h).padStart(2, "0")}
          </text>
        );
      })}
    </svg>
  );
}
