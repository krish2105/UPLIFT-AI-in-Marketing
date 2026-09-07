"use client";

import { useState } from "react";
import { LineChart, StatTile, fmt } from "@/components/charts/Chart";
import { SparkGrid, type Spark } from "@/components/charts/SparkCard";
import type { ForecastResponse, Zone } from "@/lib/api";

const DRIVER_LABEL: Record<string, string> = {
  lag_168: "Same hour last week",
  lag_336: "Same hour two weeks ago",
  roll_168_mean: "Trailing week average",
  hour: "Hour of day",
  dow: "Day of week",
  event_pull: "Event pull, distance-decayed",
  days_to_event: "Days to next event",
  apparent_c: "Apparent temperature",
  temp_c: "Temperature",
  is_ramadan: "Ramadan",
  ramadan_day: "Day of Ramadan",
  is_school_break: "School break",
  is_public_holiday: "Public holiday",
  is_weekend: "Weekend",
  humidity: "Humidity",
  precip_mm: "Precipitation",
  wind_kmh: "Wind",
  trend: "Trend",
};

export function ForecastView({
  forecast,
  zones,
}: {
  forecast: ForecastResponse;
  zones: Zone[];
}) {
  const codes = Object.keys(forecast.zones);
  const [active, setActive] = useState(codes.includes("DXB-MAR") ? "DXB-MAR" : codes[0]);
  const name = Object.fromEntries(zones.map((z) => [z.code, z.name]));
  const z = forecast.zones[active];
  const fw = forecast.forward?.[active] ?? [];

  /* Daily totals from the hourly horizon: 672 hourly points is unreadable, and
     a promo calendar is planned in days.

     THE INTERVAL DOES NOT SUM. Adding twenty-four hourly 80% intervals produces
     a daily band about five times too wide — it assumes every hour misses in
     the same direction at once. Errors are not perfectly correlated, so the
     VARIANCES add and the half-width grows with the square root of the count.
     Treating each hourly half-width as a standard error and combining in
     quadrature is the right aggregation, and the difference is visible: a band
     that reached zero on a 1,300-visitor day now sits where the data does. */
  const daily = new Map<string, { yhat: number; halfSq: number }>();
  for (const p of fw) {
    const d = p.ts.slice(0, 10);
    const cur = daily.get(d) ?? { yhat: 0, halfSq: 0 };
    const half = (p.hi - p.lo) / 2;
    daily.set(d, { yhat: cur.yhat + p.yhat, halfSq: cur.halfSq + half * half });
  }
  const days = [...daily.entries()].map(
    ([d, v]) => [d, { yhat: v.yhat, half: Math.sqrt(v.halfSq) }] as const,
  );

  const sparks: Spark[] = codes.map((code) => {
    const rows = forecast.forward?.[code] ?? [];
    const byDay = new Map<string, number>();
    for (const p of rows) {
      const d = p.ts.slice(0, 10);
      byDay.set(d, (byDay.get(d) ?? 0) + p.yhat);
    }
    return {
      code,
      name: name[code] ?? code,
      points: [...byDay.values()],
      // The card's headline number is the site's own improvement over the
      // baseline, not a demand index — labelled, because an unlabelled "1.28x"
      // beside a demand chart reads as demand.
      detail: `MAE ${forecast.zones[code].mae.toFixed(1)} vs ${forecast.zones[code].baseline_mae.toFixed(1)} naive`,
      badge: `${(forecast.zones[code].improvement * 100).toFixed(0)}% better`,
    };
  });

  const drivers = Object.entries(z.top_drivers).slice(0, 8);
  const maxDriver = Math.max(...drivers.map(([, v]) => v), 0.0001);

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile
          label="Weeks beaten, all sites"
          value={`${forecast.weeks_won}/${forecast.weeks_total}`}
          detail={`target ${Math.round(forecast.target_win_rate * 100)}% · achieved ${Math.round(forecast.win_rate * 100)}%`}
          token={forecast.meets_target ? "--pass-text" : "--fail-text"}
        />
        <StatTile
          label={`${name[active]} · absolute error`}
          value={z.mae.toFixed(2)}
          detail={`seasonal naive ${z.baseline_mae.toFixed(2)} — ${(z.improvement * 100).toFixed(0)}% better`}
        />
        <StatTile
          label="80% interval coverage"
          value={`${(z.coverage_80 * 100).toFixed(0)}%`}
          detail="share of held-out hours inside the band"
        />
        <StatTile
          label="Holdout"
          value="56 days"
          detail="chronological, never random"
        />
      </div>

      <section className="stack">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2 className="h3">Next 28 days at {name[active]}</h2>
          <div role="group" aria-label="Site" className="row" style={{ gap: "0.25rem" }}>
            {codes.map((c) => (
              <button
                key={c}
                type="button"
                className="btn"
                aria-pressed={c === active}
                onClick={() => setActive(c)}
                style={{ padding: "0.25rem 0.55rem", fontSize: "0.7rem" }}
              >
                {c}
              </button>
            ))}
          </div>
        </div>
        <p className="note">
          The band is the 80% prediction interval, fitted as two quantile models rather than
          derived from a residual standard deviation. Demand is bounded below by zero and its
          spread grows with its level, so a symmetric interval would be too wide at 04:00 and too
          narrow at the evening peak — which is exactly when a planner needs it.
        </p>
        {days.length > 0 && (
          <LineChart
            series={[
              {
                key: "yhat",
                label: "Forecast",
                token: "--sig-forecast",
                points: days.map(([, v], i) => ({ x: i, y: v.yhat })),
              },
            ]}
            xTicks={days
              .map(([d], i) => ({ at: i, label: d.slice(5) }))
              .filter((_, i) => i % Math.ceil(days.length / 7) === 0)}
            caption="Forecast daily footfall, generated series"
            yLabel="visitors per day"
            bandPoints={days.map(
              ([, v]) => [Math.max(0, v.yhat - v.half), v.yhat + v.half] as [number, number],
            )}
          />
        )}
      </section>

      <section className="stack">
        <h2 className="h3">All four sites, one scale</h2>
        <SparkGrid sparks={sparks} caption="Forecast daily footfall over the horizon" />
      </section>

      <div className="split">
        <section className="stack">
          <h2 className="h3">What moves it</h2>
          <p className="note">
            Gain-based importance from the median model. The lag terms dominate because an hourly
            retail series is mostly its own past — which is exactly why the seasonal-naive
            baseline is hard to beat, and why beating it means the exogenous drivers are earning
            their place.
          </p>
          <div className="stack" style={{ gap: "0.45rem" }}>
            {drivers.map(([k, v]) => (
              <div key={k} className="stack" style={{ gap: "0.2rem" }}>
                <div className="between faint">
                  <span>{DRIVER_LABEL[k] ?? k}</span>
                  <span className="num">{(v * 100).toFixed(1)}%</span>
                </div>
                <div style={{ height: 6, background: "var(--surface-hover)", borderRadius: 3 }}>
                  <div
                    style={{
                      width: `${(v / maxDriver) * 100}%`,
                      height: "100%",
                      background: "var(--sig-forecast)",
                      borderRadius: 3,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="stack">
          <h2 className="h3">Week by week against the baseline</h2>
          <p className="note">
            Reported per week rather than as one aggregate, because a single mean hides a model
            that wins on average by being spectacular once and worse every other week.
          </p>
          <div className="scroll-x">
            <table className="data">
              <thead>
                <tr><th>week</th><th>hours</th><th>model MAE</th><th>naive MAE</th><th>result</th></tr>
              </thead>
              <tbody>
                {z.weekly.map((w) => (
                  <tr key={w.week}>
                    <td className="num">{w.week}</td>
                    <td className="num">{w.hours}</td>
                    <td className="num">{w.mae_model.toFixed(2)}</td>
                    <td className="num">{w.mae_baseline.toFixed(2)}</td>
                    <td>
                      <span className={`badge badge-${w.won ? "pass" : "fail"}`}>
                        {w.won ? "beat" : "lost"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <section className="stack">
        <h2 className="h3">Where the model is worse, and why that is reported</h2>
        <p className="note ltr">{forecast.note_on_smape}</p>
        <div className="cards">
          <StatTile label={`${name[active]} · sMAPE`} value={`${z.smape.toFixed(1)}%`} detail={`naive ${z.baseline_smape.toFixed(1)}%`} />
          <StatTile label="Method" value="GBR" detail="absolute-error median, pinball quantiles" />
          <StatTile label="Rows fitted" value={fmt(z.weeks_total * 7 * 24 * 3)} detail="approximate, per site" />
        </div>
      </section>
    </div>
  );
}
