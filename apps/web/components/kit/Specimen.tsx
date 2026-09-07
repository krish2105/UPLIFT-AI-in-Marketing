/* One specimen, rendered identically inside every direction.
 *
 * The comparison is only honest if the markup does not change between
 * directions — otherwise you are comparing two designs AND two layouts and
 * cannot tell which one you preferred. So this component takes the direction
 * name only to pick its signature element, and everything else is shared.
 */

import { ZONES, CREATIVE, COMPLIANCE, FRESHNESS } from "@/lib/demo";
import { StationStrip } from "@/components/signatures/StationStrip";
import { MashrabiyaVeil } from "@/components/signatures/MashrabiyaVeil";
import { DaypartDial } from "@/components/signatures/DaypartDial";

export type Direction = "almanac" | "souk" | "daypart";

export const DIRECTIONS: Record<Direction, { name: string; chromaRule: string; signature: string }> = {
  almanac: {
    name: "Almanac",
    chromaRule: "Colour is temperature. One thermal ramp, plus one violet that means a human planned something here.",
    signature: "The station strip — the day's conditions in meteorological notation, on every page.",
  },
  souk: {
    name: "Night Souk",
    chromaRule: "Colour is the gap between expected and observed. Brass is the forecast, verdigris is what happened.",
    signature: "The mashrabiya veil — the aperture is the prediction interval, so an uncertain number is screened from you.",
  },
  daypart: {
    name: "Daypart",
    chromaRule: "Colour is the time of day. The three hues are the three cells of the media allocator.",
    signature: "The daypart dial — 24 hours of forecast demand, and the primary filter for the whole application.",
  },
};

function Sparkline({ shape, pi }: { shape: number[]; pi: number }) {
  const w = 180;
  const h = 40;
  const pts = shape.map((v, i) => [(i / (shape.length - 1)) * w, h - v * (h - 4) - 2]);
  const line = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  // The interval band is drawn around the line at constant half-width, which is
  // what an 80% PI on a normalised index actually looks like.
  const band = pi * (h - 4) * 2.2;
  const top = pts.map(([x, y]) => `${x.toFixed(1)},${Math.max(1, y - band).toFixed(1)}`);
  const bot = [...pts].reverse().map(([x, y]) => `${x.toFixed(1)},${Math.min(h - 1, y + band).toFixed(1)}`);

  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h} role="img"
         aria-label="24-hour forecast shape with its 80% prediction interval">
      <polygon points={[...top, ...bot].join(" ")} fill="var(--sig-forecast)" opacity="0.18" />
      <path d={line} fill="none" stroke="var(--sig-forecast)" strokeWidth="1.6" />
    </svg>
  );
}

export function Specimen({ direction }: { direction: Direction }) {
  const meta = DIRECTIONS[direction];
  const marina = ZONES[0];

  return (
    <div className="surface">
      <div className="section stack-l">
        {/* ── masthead + signature ─────────────────────────────────────── */}
        <header className="stack">
          {direction === "almanac" && <StationStrip zone={marina} hijri="24 Rabi' I 1448" />}

          <div className="between" style={{ alignItems: "flex-start" }}>
            <div className="stack" style={{ gap: "0.5rem" }}>
              <p className="eyebrow">Mawsim · Sidra · week 37</p>
              <h1 className="display">
                {direction === "daypart" ? "Evenings carry the week." : "The Walk gets its evenings back."}
              </h1>
              <p className="lede">
                Marina Walk is forecast {marina.index.toFixed(2)}× its trailing median over the Eid
                al-Adha weekend, and the interval is wide enough that the promotion should be
                sized for the low end.
              </p>
              <div className="row">
                <span className="chip chip-label">simulated</span>
                <span className="chip chip-accent">promo planned</span>
                <span className="chip">80% interval ±{marina.pi.toFixed(2)}</span>
              </div>
            </div>

            {direction === "daypart" && <DaypartDial shape={marina.shape} />}
          </div>

          {direction === "souk" && (
            <div className="stack" style={{ gap: "0.4rem" }}>
              <p className="eyebrow">Next eight days · aperture is confidence</p>
              <MashrabiyaVeil
                values={[0.62, 0.71, 0.94, 1.0, 0.88, 0.54, 0.49, 0.66]}
                intervals={[0.06, 0.08, 0.19, 0.22, 0.14, 0.07, 0.05, 0.11]}
                labels={["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN", "MON"]}
                label="Eight days of forecast demand; a wider aperture means a more confident forecast"
              />
            </div>
          )}
        </header>

        <hr className="rule" />

        {/* ── zones ────────────────────────────────────────────────────── */}
        <section className="stack">
          <p className="eyebrow">Four sites, four different answers</p>
          <div className="grid">
            {ZONES.map((z) => (
              <article key={z.code} className="card stack" style={{ gap: "0.55rem" }}>
                <div className="between">
                  <span className="code">{z.code}</span>
                  <span className="num" style={{ fontSize: "var(--step-1)" }}>{z.index.toFixed(2)}×</span>
                </div>
                <div>
                  <div className="h3">{z.name}</div>
                  <div className="faint">{z.character}</div>
                </div>
                <Sparkline shape={z.shape} pi={z.pi} />
                <div className="between faint">
                  <span>±{z.pi.toFixed(2)} at 80%</span>
                  <span className="num">{z.tempC}°C</span>
                </div>
              </article>
            ))}
          </div>
        </section>

        <hr className="rule" />

        {/* ── creative + compliance ────────────────────────────────────── */}
        <section className="stack">
          <p className="eyebrow">One slot, one variant, two verdicts</p>
          <div style={{ display: "grid", gap: "1rem", gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 17rem), 1fr))" }}>
            <div className="creative">
              <div className="code">{CREATIVE.zone} · EN</div>
              <div className="stack" style={{ gap: "0.5rem", flex: 1, justifyContent: "center" }}>
                <div className="creative-head">{CREATIVE.headline}</div>
                <div className="creative-body">{CREATIVE.body}</div>
              </div>
              <span className="creative-cta">{CREATIVE.cta}</span>
            </div>

            <div className="creative" dir="rtl" lang="ar">
              <div className="code" dir="ltr">{CREATIVE.zone} · AR</div>
              <div className="stack" style={{ gap: "0.5rem", flex: 1, justifyContent: "center" }}>
                <div className="creative-head">المساء عاد إلى المرسى.</div>
                <div className="creative-body">قهوة باردة بالهيل وكنافة بالفستق، من الساعة 5 مساءً. في مرسى دبي فقط.</div>
              </div>
              <span className="creative-cta">احجز طاولتك</span>
            </div>

            <div className="card stack" style={{ gap: "0.8rem" }}>
              <div className="between">
                <span className="eyebrow" style={{ margin: 0 }}>Compliance</span>
                <span className="faint num">seed {CREATIVE.seed}</span>
              </div>
              {COMPLIANCE.map((c) => (
                <div key={c.id} className="stack" style={{ gap: "0.3rem" }}>
                  <div className="row">
                    <span className={`badge badge-${c.verdict}`}>{c.verdict}</span>
                    <span className="code">{c.id}</span>
                  </div>
                  <div style={{ fontSize: "var(--step--1)" }}>{c.claim}</div>
                  <div className="faint">
                    {c.rule} <span className="num">[{c.citations}]</span> {c.source}
                  </div>
                </div>
              ))}
              <div className="between">
                <span className="faint">Persona panel, n={CREATIVE.panelN}</span>
                <span className="num" style={{ fontSize: "var(--step-1)" }}>{CREATIVE.panel.toFixed(1)}</span>
              </div>
            </div>
          </div>
        </section>

        <hr className="rule" />

        {/* ── data ─────────────────────────────────────────────────────── */}
        <section className="stack">
          <p className="eyebrow">Every dataset says what it is</p>
          <div className="scroll-x">
            <table className="data">
              <thead>
                <tr><th>dataset</th><th>rows</th><th>span</th><th>label</th><th>licence</th></tr>
              </thead>
              <tbody>
                {FRESHNESS.map((d) => (
                  <tr key={d.name}>
                    <td className="num">{d.name}</td>
                    <td className="num">{d.rows}</td>
                    <td className="num">{d.span}</td>
                    <td><span className="chip chip-label">{d.label}</span></td>
                    <td className="muted">{d.licence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <hr className="rule" />

        {/* ── the palette, stated as a rule rather than shown as swatches ── */}
        <section className="stack">
          <p className="eyebrow">The one chroma rule</p>
          <p className="body">{meta.chromaRule}</p>
          <div className="ramp" aria-hidden="true">
            {["--heat-0", "--heat-1", "--heat-2", "--heat-3", "--heat-4", "--heat-5"].map((t) => (
              <i key={t} style={{ background: `var(${t})` }} />
            ))}
          </div>
          <p className="faint">{meta.signature}</p>
        </section>
      </div>
    </div>
  );
}
