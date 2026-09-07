"use client";

import { useEffect, useState } from "react";
import { LineChart, StatTile, DAYPART_TOKEN, fmt } from "@/components/charts/Chart";
import { api, type AllocatorResponse } from "@/lib/api";

const DAYPARTS = ["morning", "midday", "evening"] as const;

export function PlanView({ initial }: { initial: AllocatorResponse }) {
  const [budget, setBudget] = useState(initial.budget);
  const [data, setData] = useState(initial);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (budget === data.budget) return;
    let live = true;
    setBusy(true);
    const id = setTimeout(() => {
      api
        .allocator(budget)
        .then((d) => live && setData(d))
        .catch(() => {})
        .finally(() => live && setBusy(false));
    }, 180);
    return () => {
      live = false;
      clearTimeout(id);
    };
  }, [budget, data.budget]);

  const channels = [...new Set(data.cells.map((c) => c.channel))];
  const maxSpend = Math.max(...data.cells.map((c) => c.spend), 1);
  const allocated = data.cells.reduce((a, c) => a + c.spend, 0);

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile label="Budget" value={`${fmt(Math.round(budget))} AED`} detail="drag to re-solve" />
        <StatTile
          label="Incremental visits"
          value={fmt(Math.round(data.total_response))}
          detail={`${(data.total_response / budget * 1000).toFixed(1)} per 1,000 AED`}
          token="--accent"
        />
        <StatTile
          label="Allocated"
          value={`${fmt(Math.round(allocated))} AED`}
          detail={Math.abs(allocated - budget) < 1 ? "sums exactly to budget" : "DOES NOT SUM"}
          token={Math.abs(allocated - budget) < 1 ? "--pass-text" : "--fail-text"}
        />
        <StatTile
          label="Marginal spread"
          value={data.marginal_spread.toExponential(1)}
          detail="0 = equal marginal return, the KKT optimum"
          token={data.marginal_spread < 0.01 ? "--pass-text" : "--fail-text"}
        />
      </div>

      <section className="stack">
        <label className="stack" style={{ gap: "0.4rem" }}>
          <span className="eyebrow" style={{ margin: 0 }}>
            Budget · {fmt(Math.round(budget))} AED {busy ? "· solving" : ""}
          </span>
          <input
            type="range"
            min={1000}
            max={40000}
            step={500}
            value={budget}
            onChange={(e) => setBudget(Number(e.target.value))}
            aria-label="Campaign budget in dirhams"
            style={{ width: "100%", accentColor: "var(--accent)" }}
          />
        </label>
        <p className="note">
          Each cell&rsquo;s response saturates, so the total is concave and a greedy marginal
          allocation reaches the exact optimum — not an approximation of one. The check is the
          marginal spread above: at the optimum every funded cell returns the same amount for the
          next dirham.
        </p>
      </section>

      <div className="row">
        <span className="chip chip-label">assumed elasticities</span>
        <span className="chip">not fitted</span>
      </div>
      <p className="note ltr">{data.note}</p>

      <section className="stack">
        <h2 className="h3">Where the money goes</h2>
        <div className="scroll-x">
          <table className="data">
            <thead>
              <tr>
                <th>channel</th>
                {DAYPARTS.map((d) => <th key={d}>{d}</th>)}
                <th>total</th>
              </tr>
            </thead>
            <tbody>
              {channels.map((ch) => {
                const row = DAYPARTS.map((dp) =>
                  data.cells.find((c) => c.channel === ch && c.daypart === dp),
                );
                const total = row.reduce((a, c) => a + (c?.spend ?? 0), 0);
                return (
                  <tr key={ch}>
                    <td>{data.cells.find((c) => c.channel === ch)?.label ?? ch}</td>
                    {row.map((c, i) => (
                      <td key={i} className="num">
                        <span
                          style={{
                            display: "inline-block",
                            minWidth: "3.5rem",
                            padding: "0.1rem 0.35rem",
                            borderRadius: "var(--radius)",
                            background:
                              c && c.spend > 0
                                ? `color-mix(in oklab, var(${DAYPART_TOKEN[DAYPARTS[i]]}) ${Math.round((c.spend / maxSpend) * 70) + 12}%, transparent)`
                                : "transparent",
                          }}
                        >
                          {c && c.spend > 0 ? fmt(Math.round(c.spend)) : "—"}
                        </span>
                      </td>
                    ))}
                    <td className="num">{fmt(Math.round(total))}</td>
                  </tr>
                );
              })}
              <tr>
                <td className="faint">total</td>
                {DAYPARTS.map((d) => (
                  <td key={d} className="num">{fmt(Math.round(data.by_daypart[d] ?? 0))}</td>
                ))}
                <td className="num">{fmt(Math.round(allocated))}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <p className="faint">
          Cell shading is the thermal ramp by daypart — morning at the cool end, evening at the
          warm end — so the table reads as a heat map without introducing a colour that competes
          with it.
        </p>
      </section>

      <section className="stack">
        <h2 className="h3">Diminishing returns</h2>
        <p className="note">
          The curve the slider moves along. Concavity is not decoration: it is why there is a
          right answer at all, and why the second ten thousand dirhams buys less than the first.
        </p>
        <LineChart
          series={[
            {
              key: "response",
              label: "Incremental visits",
              token: "--accent",
              points: data.sweep.map((s, i) => ({ x: i, y: s.response })),
            },
          ]}
          xTicks={data.sweep.map((s, i) => ({ at: i, label: `${s.budget / 1000}k` }))}
          caption="Total response against budget"
          yLabel="incremental visits"
        />
      </section>
    </div>
  );
}
