"use client";

import { LineChart, StatTile } from "@/components/charts/Chart";
import type { ExperimentsResponse } from "@/lib/api";

export function ExperimentsView({ data }: { data: ExperimentsResponse }) {
  const here = data.by_zone.find((z) => z.zone === data.zone) ?? data.by_zone[0];
  const cheapest = [...data.by_zone].sort((a, b) => a.mde_pct - b.mde_pct)[0];
  const dearest = [...data.by_zone].sort((a, b) => b.mde_pct - a.mde_pct)[0];

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile
          label={`${here.zone} · MDE over ${data.days} days`}
          value={`${here.mde_pct.toFixed(1)}%`}
          detail="the smallest lift this window could distinguish from noise"
          token="--heat-4"
        />
        <StatTile label="Cheapest site to measure" value={cheapest.zone} detail={`${cheapest.mde_pct.toFixed(1)}% at ${data.days} days`} token="--pass-text" />
        <StatTile label="Dearest" value={dearest.zone} detail={`${dearest.mde_pct.toFixed(1)}% — needs a longer window`} token="--fail-text" />
        <StatTile label="Design" value="95 / 80" detail="confidence and power" />
      </div>

      <p className="note ltr">{data.method}</p>

      <section className="stack">
        <h2 className="h3">How long the window has to be</h2>
        <p className="note">
          Detectability improves with the square root of the window, so doubling a promotion&rsquo;s
          length buys about a 30% smaller detectable effect — not half. That is why a three-day
          promotion is usually not worth measuring: at {data.sweep[0]?.mde_pct.toFixed(1)}% the
          effect would have to be implausibly large to show up at all.
        </p>
        <LineChart
          series={[
            {
              key: "mde",
              label: "Minimum detectable effect",
              token: "--heat-4",
              points: data.sweep.map((s, i) => ({ x: i, y: s.mde_pct })),
            },
          ]}
          xTicks={data.sweep.map((s, i) => ({ at: i, label: `${s.days}d` }))}
          caption={`${data.zone} · smallest lift detectable at 95% confidence and 80% power`}
          yLabel="percent lift"
        />
      </section>

      <section className="stack">
        <h2 className="h3">Every site, at {data.days} days</h2>
        <div className="scroll-x">
          <table className="data">
            <thead>
              <tr><th>site</th><th>daily mean</th><th>gap sd</th><th>MDE</th><th>donors</th></tr>
            </thead>
            <tbody>
              {data.by_zone.map((z) => (
                <tr key={z.zone}>
                  <td className="num">{z.zone}</td>
                  <td className="num">{Math.round(z.daily_mean).toLocaleString("en-GB")}</td>
                  <td className="num">{z.gap_sd.toFixed(1)}</td>
                  <td className="num">{z.mde_pct.toFixed(2)}%</td>
                  <td className="faint num">{z.donors.join(" ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="faint">
          Deira has the smallest absolute traffic and the largest detectable effect, because its
          gap to the synthetic control is noisy relative to its own size. It is the site where a
          promotion is hardest to prove worked.
        </p>
      </section>

      <section className="stack">
        <h2 className="h3">Pre-registration</h2>
        <p className="note ltr">{data.note}</p>
        <div className="cards">
          <StatTile label="Metric" value="Incremental visits" detail="fixed before the window opens" />
          <StatTile label="Holdout" value="The other three sites" detail="donor pool for the synthetic control" />
          <StatTile label="Analysis" value="Synthetic control + CUPED" detail="chosen in advance, not after the result" />
        </div>
      </section>
    </div>
  );
}
