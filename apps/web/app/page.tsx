import { ThemeToggle } from "@/components/ThemeToggle";
import { MashrabiyaVeil } from "@/components/signatures/MashrabiyaVeil";
import { DaypartDial } from "@/components/signatures/DaypartDial";
import { ZONES } from "@/lib/demo";

/* The holding page. Task A10 replaces this with the fifteen-tab shell; until
 * then it exists so the design system, both registers and both signature
 * components are running and verifiable rather than only committed.
 */
export default function Home() {
  const marina = ZONES[0];

  return (
    <main className="surface" style={{ minHeight: "100dvh" }}>
      <div className="section stack-l">
        <header className="between" style={{ alignItems: "flex-start" }}>
          <div className="stack" style={{ gap: "0.4rem" }}>
            <p className="eyebrow">Mawsim · AI 208 · SP Jain MAIB Term 4</p>
            <h1 className="display">Evenings carry the week.</h1>
          </div>
          <ThemeToggle />
        </header>

        <div className="between" style={{ alignItems: "flex-start", gap: "2rem" }}>
          <p className="lede">
            Demand-aware promo planning for SIDRA — a fictional Dubai speciality coffee and
            bakery chain, invented for this coursework demonstration. The footfall it is planned
            against is simulated, and says so everywhere it appears.
          </p>
          <DaypartDial shape={marina.shape} />
        </div>

        <div className="row">
          <span className="chip chip-label">simulated</span>
          <span className="chip">4 zones</span>
          <span className="chip">80% interval ±{marina.pi.toFixed(2)}</span>
        </div>

        <hr className="rule" />

        <section className="stack">
          <p className="eyebrow">Next eight days · aperture is confidence</p>
          <MashrabiyaVeil
            values={[0.62, 0.71, 0.94, 1.0, 0.88, 0.54, 0.49, 0.66]}
            intervals={[0.06, 0.08, 0.19, 0.22, 0.14, 0.07, 0.05, 0.11]}
            labels={["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN", "MON"]}
            label="Eight days of forecast demand; a wider aperture is a more confident forecast"
          />
          <p className="faint">
            Wednesday and Thursday are screened almost shut because their prediction intervals
            are the widest on the horizon. Uncertainty is drawn as an obstacle rather than as a
            fainter shade, so it reads as less known rather than as less important.
          </p>
        </section>
      </div>
    </main>
  );
}
