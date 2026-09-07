"use client";

/* ALMANAC's signature: the station strip.
 *
 * A meteorological station model is a fixed notation — temperature at upper
 * left, humidity below it, a barb showing wind speed and direction, the sky
 * condition in the circle — that a forecaster reads at a glance without reading
 * any words. This is that notation carrying SIDRA's variables instead of a
 * synoptic chart's: forecast temperature, humidity, wind, the Hijri date, and
 * the demand index with its prediction interval drawn as a BRACKET rather than
 * printed as a number.
 *
 * The bracket is the point. A printed "±0.19" invites you to read it as a
 * precise fact about imprecision. A bracket that grows as the interval widens
 * is read as width, which is what it is.
 *
 * It appears on every page, because the claim the direction makes is that a
 * promo planner should be able to read the day's conditions the way a
 * forecaster reads a chart.
 */

export type Station = {
  zone: string;
  tempC: number;
  humidity: number;
  windKmh: number;
  hijri: string;
  index: number;
  pi: number;
};

/** Wind barbs: a full barb per 10 km/h, a half barb for 5. Real notation. */
function barbs(kmh: number) {
  const full = Math.floor(kmh / 10);
  const half = kmh % 10 >= 5;
  return { full: Math.min(full, 4), half };
}

export function StationStrip({ station }: { station: Station }) {
  const { full, half } = barbs(station.windKmh);
  // The bracket's width IS the interval, clamped so it stays legible at both ends.
  const bracket = Math.min(64, Math.max(10, station.pi * 190));

  return (
    <div className="station" role="group" aria-label="Current station report">
      <div className="station-left">
        <svg width="52" height="30" viewBox="0 0 52 30" aria-hidden="true" className="station-model">
          <text x="0" y="11" fontSize="8.5" fill="var(--heat-5)" fontFamily="var(--font-mono)">
            {Math.round(station.tempC)}
          </text>
          <text x="0" y="26" fontSize="8" fill="var(--text-faint)" fontFamily="var(--font-mono)">
            {Math.round(station.humidity)}
          </text>
          {/* sky condition: an open circle is clear, which Dubai mostly is */}
          <circle cx="26" cy="15" r="5.5" fill="none" stroke="var(--text-faint)" strokeWidth="1.2" />
          {/* the shaft points into the wind; barbs hang off its end */}
          <line x1="31.5" y1="15" x2="46" y2="8" stroke="var(--text-muted)" strokeWidth="1.2" />
          {Array.from({ length: full }).map((_, i) => (
            <line
              key={i}
              x1={46 - i * 3.4}
              y1={8 + i * 1.6}
              x2={42 - i * 3.4}
              y2={3.4 + i * 1.6}
              stroke="var(--text-muted)"
              strokeWidth="1.2"
            />
          ))}
          {half && (
            <line
              x1={46 - full * 3.4}
              y1={8 + full * 1.6}
              x2={44 - full * 3.4}
              y2={5.8 + full * 1.6}
              stroke="var(--text-muted)"
              strokeWidth="1.2"
            />
          )}
        </svg>

        <span className="station-sep" aria-hidden="true">│</span>
        <span className="station-field">
          <span className="station-key">ZONE</span>
          <span className="station-val">{station.zone}</span>
        </span>
        <span className="station-field station-hijri">
          <span className="station-key">HIJRI</span>
          <span className="station-val">{station.hijri}</span>
        </span>
      </div>

      <div className="station-right">
        <span className="station-key">DEMAND IDX</span>
        <span className="station-idx">{station.index.toFixed(2)}</span>
        <svg
          width={bracket}
          height="12"
          viewBox={`0 0 ${bracket} 12`}
          role="img"
          aria-label={`80 percent prediction interval, plus or minus ${station.pi.toFixed(2)}`}
        >
          <line x1="1" y1="2" x2="1" y2="10" stroke="var(--text-faint)" strokeWidth="1.2" />
          <line x1={bracket - 1} y1="2" x2={bracket - 1} y2="10" stroke="var(--text-faint)" strokeWidth="1.2" />
          <line x1="1" y1="6" x2={bracket - 1} y2="6" stroke="var(--text-faint)" strokeWidth="1.2" />
        </svg>
        <span className="station-key">±{station.pi.toFixed(2)}</span>
      </div>
    </div>
  );
}
