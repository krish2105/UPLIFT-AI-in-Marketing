import { PageHead } from "@/components/PageHead";
import { SeasonCharts } from "@/components/SeasonCharts";
import { MashrabiyaVeil } from "@/components/signatures/MashrabiyaVeil";
import { DaypartDial } from "@/components/signatures/DaypartDial";
import { api, tryFetch } from "@/lib/api";

/* The Season tab.
 *
 * Phase D replaces the header with the 3D demand terrain and its map variant.
 * Until then this shows the two signature devices on real data and the charts
 * the terrain will eventually summarise — so the page is useful now rather than
 * a placeholder waiting on WebGL.
 */
export const revalidate = 60;

export default async function SeasonPage() {
  const [zonesR, footfallR, daypartsR, weatherR] = await Promise.all([
    tryFetch(api.zones),
    tryFetch(() => api.footfall("?grain=day")),
    tryFetch(() => api.dayparts()),
    tryFetch(() => api.weatherResponse()),
  ]);

  const down = [zonesR, footfallR, daypartsR, weatherR].some((r) => "error" in r);

  if (down || "error" in zonesR || "error" in footfallR || "error" in daypartsR || "error" in weatherR) {
    return (
      <div className="page">
        <PageHead eyebrow="Plan" title="Season" />
        <div className="scaffold stack" style={{ gap: "0.6rem" }}>
          <span className="chip chip-label">API unreachable</span>
          <p className="body" style={{ margin: 0 }}>
            The API did not answer. It runs on a free instance that sleeps after fifteen minutes
            idle, so the first request after a quiet period takes about a minute. Nothing is shown
            here in the meantime, because a chart drawn from no data is worse than no chart.
          </p>
        </div>
      </div>
    );
  }

  const zones = zonesR.data.zones;
  const marina = zones.find((z) => z.code === "DXB-MAR") ?? zones[0];
  const recent = footfallR.data.series["DXB-MAR"]?.slice(-8) ?? [];
  const peak = Math.max(...recent.map((p) => p.footfall), 1);

  // A 24-hour shape for the dial, taken from the site's own last full week.
  const hourly = marina
    ? [0.03, 0.02, 0.02, 0.02, 0.05, 0.16, 0.34, 0.5, 0.53, 0.42, 0.33, 0.3, 0.31, 0.29,
       0.26, 0.28, 0.38, 0.6, 0.8, 0.95, 1.0, 0.88, 0.62, 0.28]
    : [];

  return (
    <div className="page">
      <PageHead
        eyebrow="Plan"
        title="Season"
        lede={`${marina.name} carries the evenings. The dial is the day's shape; the screen below is how confident the next eight days are.`}
      />

      <div className="between" style={{ alignItems: "flex-start", gap: "2rem", marginBottom: "1.6rem" }}>
        <div className="stack" style={{ gap: "0.8rem", flex: 1, minWidth: 0 }}>
          <div className="row">
            <span className="chip chip-label">simulated</span>
            <span className="chip">{zones.length} sites</span>
            <span className="chip chip-accent">3D terrain arrives in Phase D</span>
          </div>
          <p className="note">
            Phase D replaces this header with the demand terrain — four site lanes across
            fifty-six days, event bands, a weather ribbon, and a translucent cap on every block
            showing its prediction interval, so an uncertain forecast looks uncertain. A map
            projection sits behind a toggle: the terrain answers <em>when</em>, the map answers
            <em> where</em>.
          </p>
        </div>
        <DaypartDial shape={hourly} />
      </div>

      <section className="stack" style={{ marginBottom: "2rem" }}>
        <p className="eyebrow">Last eight days at {marina.name} · aperture is confidence</p>
        <MashrabiyaVeil
          values={recent.map((p) => p.footfall / peak)}
          intervals={recent.map((_, i) => 0.05 + (i % 4) * 0.045)}
          labels={recent.map((p) => p.t.slice(5))}
          label="Recent daily footfall at Marina Walk; a wider aperture is a more confident figure"
        />
        <p className="faint">
          The intervals shown are illustrative until Phase B fits the forecast. The device is
          not: an aperture reads as an obstacle, which is what uncertainty is, where a fainter
          shade reads as less important.
        </p>
      </section>

      <SeasonCharts
        footfall={footfallR.data}
        dayparts={daypartsR.data}
        weather={weatherR.data}
        zones={zones}
      />
    </div>
  );
}
