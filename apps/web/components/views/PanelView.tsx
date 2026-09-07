"use client";

import { StatTile } from "@/components/charts/Chart";
import type { CreativesResponse } from "@/lib/api";

const CRITERIA = ["clarity", "specificity", "fit_to_daypart", "brand_voice"] as const;
const CRITERION_LABEL: Record<string, string> = {
  clarity: "Clarity",
  specificity: "Specificity",
  fit_to_daypart: "Fit to daypart",
  brand_voice: "Brand voice",
};

export function PanelView({ data }: { data: CreativesResponse }) {
  const english = data.creatives.filter((c) => c.lang === "en");
  const personas = english[0]?.panel.scores ?? [];
  const best = [...english].sort((a, b) => b.panel.mean - a.panel.mean)[0];
  const worst = [...english].sort((a, b) => a.panel.mean - b.panel.mean)[0];

  return (
    <div className="stack-l">
      <div className="row">
        <span className="chip chip-label">not customer research</span>
        <span className="chip">deterministic under seed</span>
      </div>

      <div className="cards">
        <StatTile label="Personas" value={String(personas.length)} detail="each publishes its own bias" />
        <StatTile label="Best scoring" value={best?.slot ?? "—"} detail={`${best?.panel.mean.toFixed(2)} / 10`} token="--pass-text" />
        <StatTile label="Worst scoring" value={worst?.slot ?? "—"} detail={`${worst?.panel.mean.toFixed(2)} / 10`} token="--fail-text" />
        <StatTile label="Criteria" value="4" detail="clarity, specificity, daypart fit, voice" />
      </div>

      <p className="note">
        The panel&rsquo;s most useful single behaviour is discounting a creative aimed at the wrong
        hour: a morning persona drops a well-written evening ad by three points on daypart fit,
        which catches a good ad pointed at the wrong slot before a human spends attention on it.
      </p>

      <section className="stack">
        <h2 className="h3">Scores by slot</h2>
        <div className="scroll-x">
          <table className="data">
            <thead>
              <tr>
                <th>slot</th>
                {personas.map((p) => <th key={p.persona}>{p.persona.replace(/_/g, " ")}</th>)}
                <th>mean</th><th>spread</th>
              </tr>
            </thead>
            <tbody>
              {english.map((c) => (
                <tr key={c.slot}>
                  <td className="num">{c.slot}</td>
                  {personas.map((p) => {
                    const s = c.panel.scores.find((x) => x.persona === p.persona);
                    return (
                      <td key={p.persona} className="num">
                        <span style={{
                          display: "inline-block", minWidth: "2.6rem", padding: "0.1rem 0.3rem",
                          borderRadius: "var(--radius)",
                          background: `color-mix(in oklab, var(--sig-forecast) ${Math.round((s?.total ?? 0) * 7)}%, transparent)`,
                        }}>
                          {s?.total.toFixed(1) ?? "—"}
                        </span>
                      </td>
                    );
                  })}
                  <td className="num">{c.panel.mean.toFixed(2)}</td>
                  <td className="num">{c.panel.spread.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="faint">
          Spread matters as much as the mean. A creative every persona scores 6 is a different
          thing from one scored 9 and 3 — the second has found an audience and lost another.
        </p>
      </section>

      <section className="stack">
        <h2 className="h3">Who is on the panel, and what each gets wrong</h2>
        <div className="split">
          {personas.map((p) => (
            <article key={p.persona} className="card stack" style={{ gap: "0.4rem" }}>
              <div className="between">
                <span className="code">{p.persona}</span>
                <span className="num">{p.total.toFixed(2)}</span>
              </div>
              <div className="h3">{p.name}</div>
              <p className="faint ltr" style={{ margin: 0 }}>{p.note}</p>
              <div className="stack" style={{ gap: "0.25rem" }}>
                {CRITERIA.map((c) => (
                  <div key={c} className="stack" style={{ gap: "0.15rem" }}>
                    <div className="between faint">
                      <span>{CRITERION_LABEL[c]}</span>
                      <span className="num">{p.criteria[c]?.toFixed(1) ?? "—"}</span>
                    </div>
                    <div style={{ height: 4, background: "var(--surface-hover)", borderRadius: 2 }}>
                      <div style={{ width: `${(p.criteria[c] ?? 0) * 10}%`, height: "100%",
                                    background: "var(--sig-forecast)", borderRadius: 2 }} />
                    </div>
                  </div>
                ))}
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="stack">
        <h2 className="h3">What this is not</h2>
        <p className="note">
          It does not observe a reaction; it applies a rubric. Treating a panel score as evidence
          about real customers would be the single worst misuse of this application — so every
          persona states what it over- and under-weights, the panel reports its spread as well as
          its mean, and the score is computed in code rather than by a model, so it is the same
          number every time it is asked.
        </p>
      </section>
    </div>
  );
}
