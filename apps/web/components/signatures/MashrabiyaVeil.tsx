/* NIGHT SOUK's signature: the mashrabiya veil.
 *
 * A mashrabiya is the carved wooden screen on an old Gulf house: it filters
 * light and sight without closing them off. Here the screen sits over the
 * forecast, and each aperture's OPENING is the inverse of that day's
 * prediction interval — a confident forecast opens the lattice and you see
 * straight through to the value; an uncertain one closes it and the number is
 * literally screened from you.
 *
 * This is the direction's answer to "where could a chart mislead?". Most
 * interfaces render uncertainty as a fainter shade, which reads as "less
 * important" rather than "less known". An aperture reads as an obstacle,
 * which is what uncertainty actually is.
 *
 * Each day is its own square SVG in a flex row rather than one wide SVG,
 * because a single stretched viewBox turns the apertures into ellipses and an
 * ellipse is not a hole in a screen — it is a smear.
 */

export function MashrabiyaVeil({
  values,
  intervals,
  labels,
  label,
}: {
  values: number[];
  intervals: number[];
  labels?: string[];
  label: string;
}) {
  const max = Math.max(...values, 1);

  return (
    <div role="img" aria-label={label} style={{ display: "flex", gap: "0.35rem", width: "100%" }}>
      {values.map((v, i) => {
        // Aperture: 1 = wide open (certain), 0 = shut (unknown).
        const aperture = Math.max(0.14, 1 - intervals[i] * 3.4);
        const r = 21 * aperture;
        const intensity = v / max;
        return (
          <div key={i} style={{ flex: 1, minWidth: 0 }}>
            <svg viewBox="0 0 60 60" width="100%" aria-hidden="true" style={{ display: "block" }}>
              {/* the frame of one screen panel */}
              <rect x="1" y="1" width="58" height="58" fill="none" stroke="var(--border)" strokeWidth="1" />
              {/* the lattice bars that remain when the aperture closes */}
              <line x1="1" y1="30" x2={30 - r} y2="30" stroke="var(--rule)" strokeWidth="1" />
              <line x1={30 + r} y1="30" x2="59" y2="30" stroke="var(--rule)" strokeWidth="1" />
              <line x1="30" y1="1" x2="30" y2={30 - r} stroke="var(--rule)" strokeWidth="1" />
              <line x1="30" y1={30 + r} x2="30" y2="59" stroke="var(--rule)" strokeWidth="1" />
              {/* the opening, and the light coming through it */}
              <circle cx="30" cy="30" r={r} fill="var(--sig-forecast)" opacity={0.2 + intensity * 0.7} />
              <circle cx="30" cy="30" r={r} fill="none" stroke="var(--sig-forecast)" strokeWidth="1.2" />
            </svg>
            {labels?.[i] && (
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.62rem",
                  letterSpacing: "0.08em",
                  textAlign: "center",
                  color: "var(--text-faint)",
                  paddingTop: "0.3rem",
                }}
              >
                {labels[i]}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
