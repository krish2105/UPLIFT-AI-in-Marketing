"use client";

import { LineChart, StatTile, fmt } from "@/components/charts/Chart";
import type { UpliftResponse } from "@/lib/api";

const pct = (v: number) => `${v >= 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;

export function MeasureView({ data }: { data: UpliftResponse }) {
  const promoIdx = data.series
    .map((s, i) => (s.in_promo ? i : -1))
    .filter((i) => i >= 0);

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile
          label="Measured lift"
          value={pct(data.lift_adjusted)}
          detail={`raw ${pct(data.lift_raw)}, less ${pct(data.bias)} estimator bias`}
          token="--accent"
        />
        <StatTile
          label="Permutation p"
          value={data.placebo_p.toFixed(2)}
          detail={`against ${Object.keys(data.weights).length} donor sites`}
        />
        <StatTile
          label="Pre-period fit"
          value={data.pre_rmse.toFixed(0)}
          detail="RMSE of the synthetic control before the window"
        />
        <StatTile
          label="Recovery check"
          value={`±${data.worst_error_points.toFixed(1)} pts`}
          detail={data.all_within_tolerance ? "all five inside a 5-point tolerance" : "OUT OF TOLERANCE"}
          token={data.all_within_tolerance ? "--pass-text" : "--fail-text"}
        />
      </div>

      <section className="stack">
        <h2 className="h3">{data.treated} against its synthetic control</h2>
        <p className="note">
          The control is a weighted blend of the other sites, with weights chosen to reproduce
          this site&rsquo;s pre-period. Weights are non-negative and sum to one, so the control is
          always a convex blend of things that actually happened rather than an extrapolation
          that can go anywhere.
        </p>
        <LineChart
          series={[
            {
              key: "actual",
              label: `${data.treated} actual`,
              token: "--sig-actual",
              points: data.series.map((s, i) => ({ x: i, y: s.actual })),
            },
            {
              key: "cf",
              label: "Synthetic control",
              token: "--sig-forecast",
              points: data.series.map((s, i) => ({ x: i, y: s.counterfactual })),
            },
          ]}
          xTicks={data.series
            .map((s, i) => ({ at: i, label: s.date.slice(5) }))
            .filter((_, i) => i % Math.ceil(data.series.length / 7) === 0)}
          caption={`Daily footfall · promotion window ${data.window[0]} to ${data.window[1]} (points ${promoIdx[0]}–${promoIdx[promoIdx.length - 1]})`}
          yLabel="visitors per day"
        />
        <div className="row">
          {Object.entries(data.weights).map(([z, w]) => (
            <span key={z} className="chip">
              {z} <span className="num">{(w * 100).toFixed(0)}%</span>
            </span>
          ))}
        </div>
      </section>

      <section className="stack">
        <h2 className="h3">The estimator&rsquo;s own bias, measured</h2>
        <div className="row">
          <span className="chip chip-label">placebo in time</span>
          <span className="chip">{pct(data.bias)}</span>
        </div>
        <p className="note ltr">{data.note_on_bias}</p>
      </section>

      <section className="stack">
        <h2 className="h3">Does it find a lift it was handed?</h2>
        <p className="note">
          The check that makes every number above worth reading. A known lift is injected into
          the series and the same machinery is asked to find it. An estimator that cannot recover
          a lift it was given is not measuring anything.
        </p>
        <div className="scroll-x">
          <table className="data">
            <thead>
              <tr><th>injected</th><th>raw</th><th>bias</th><th>adjusted</th><th>error</th><th>result</th></tr>
            </thead>
            <tbody>
              {data.recovery.map((r) => (
                <tr key={r.injected}>
                  <td className="num">{pct(r.injected)}</td>
                  <td className="num">{pct(r.recovered_raw)}</td>
                  <td className="num">{pct(r.bias)}</td>
                  <td className="num">{pct(r.recovered)}</td>
                  <td className="num">{r.error_points >= 0 ? "+" : ""}{r.error_points.toFixed(2)} pts</td>
                  <td>
                    <span className={`badge badge-${r.within_5_points ? "pass" : "fail"}`}>
                      {r.within_5_points ? "within 5" : "outside"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="stack">
        <h2 className="h3">Totals over the window</h2>
        <div className="cards">
          <StatTile label="Observed" value={fmt(Math.round(data.treated_total))} detail="visitors, treated site" />
          <StatTile label="Counterfactual" value={fmt(Math.round(data.counterfactual_total))} detail="what the control says would have happened" />
          <StatTile label="CUPED variance reduction" value={`${(data.variance_reduction * 100).toFixed(0)}%`} detail="narrower interval, same point estimate" />
        </div>
        <p className="note ltr">{data.method}</p>
      </section>
    </div>
  );
}
