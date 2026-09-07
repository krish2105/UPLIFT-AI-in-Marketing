"use client";

import { StatTile, fmt } from "@/components/charts/Chart";
import type { SegmentsResponse } from "@/lib/api";

/* The heat ramp carries segment value here, which is consistent with the one
 * chroma rule: it is a MAGNITUDE, so it gets a position on the sequential ramp
 * rather than a hue of its own. */
const RAMP = ["--heat-5", "--heat-4", "--heat-3", "--heat-2", "--heat-1", "--heat-0", "--heat-0"];

export function SegmentsView({ data }: { data: SegmentsResponse }) {
  const rows = [...data.segments].sort((a, b) => b.revenue - a.revenue);
  const maxRevenue = Math.max(...rows.map((r) => r.revenue), 1);
  const top = rows[0];

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile label="Customers" value={fmt(data.customers)} detail={`sample as of ${data.as_of}`} />
        <StatTile
          label="Bootstrap stability"
          value={`${(data.bootstrap_stability * 100).toFixed(1)}%`}
          detail="keep their segment across 25 resamples"
          token={data.bootstrap_stability >= 0.8 ? "--pass-text" : "--fail-text"}
        />
        <StatTile
          label={`${top.segment} share`}
          value={`${(top.revenue_share * 100).toFixed(0)}%`}
          detail={`of revenue, from ${(top.customer_share * 100).toFixed(0)}% of customers`}
          token="--heat-5"
        />
        <StatTile label="Segments" value={String(rows.length)} detail="a decision list, first match wins" />
      </div>

      <p className="note ltr">{data.method}</p>

      <section className="stack">
        <h2 className="h3">Revenue by segment</h2>
        <div className="stack" style={{ gap: "0.9rem" }}>
          {rows.map((r, i) => (
            <div key={r.segment} className="stack" style={{ gap: "0.3rem" }}>
              <div className="between">
                <span className="row" style={{ gap: "0.5rem" }}>
                  <strong>{r.segment}</strong>
                  <span className="faint num">{fmt(r.customers)} customers</span>
                </span>
                <span className="num">{fmt(Math.round(r.revenue))} AED</span>
              </div>
              <div style={{ height: 10, background: "var(--surface-hover)", borderRadius: 3 }}>
                <div
                  style={{
                    width: `${(r.revenue / maxRevenue) * 100}%`,
                    height: "100%",
                    background: `var(${RAMP[i] ?? "--heat-0"})`,
                    borderRadius: 3,
                  }}
                />
              </div>
              <p className="faint ltr" style={{ margin: 0 }}>{r.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="stack">
        <h2 className="h3">The numbers behind them</h2>
        <div className="scroll-x">
          <table className="data">
            <thead>
              <tr>
                <th>segment</th><th>customers</th><th>revenue</th><th>avg basket</th>
                <th>median recency</th><th>median visits</th><th>revenue share</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.segment}>
                  <td>{r.segment}</td>
                  <td className="num">{fmt(r.customers)}</td>
                  <td className="num">{fmt(Math.round(r.revenue))}</td>
                  <td className="num">{r.avg_basket.toFixed(2)}</td>
                  <td className="num">{r.median_recency}d</td>
                  <td className="num">{r.median_frequency}</td>
                  <td className="num">{(r.revenue_share * 100).toFixed(1)}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="stack">
        <h2 className="h3">Response curves</h2>
        <div className="row">
          <span className="chip chip-label">assumed</span>
          <span className="chip">not fitted</span>
        </div>
        <p className="note ltr">{data.note_on_curves}</p>
        <div className="scroll-x">
          <table className="data">
            <thead>
              <tr><th>segment</th><th>ceiling</th><th>saturation rate</th><th>customers</th></tr>
            </thead>
            <tbody>
              {data.response_curves.map((c) => (
                <tr key={c.segment}>
                  <td>{c.segment}</td>
                  <td className="num">{(c.ceiling * 100).toFixed(0)}%</td>
                  <td className="num">{c.saturation_rate.toFixed(2)}</td>
                  <td className="num">{fmt(c.customers)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
