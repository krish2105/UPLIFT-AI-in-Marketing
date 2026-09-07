"use client";

import { useState } from "react";
import { StatTile } from "@/components/charts/Chart";
import type { CreativesResponse, CreativeItem } from "@/lib/api";

const LANG_LABEL: Record<string, string> = { en: "English", ar: "العربية", hi: "हिन्दी" };

function Verdict({ item }: { item: CreativeItem }) {
  const v = item.compliance;
  return (
    <div className="stack" style={{ gap: "0.45rem" }}>
      <div className="row">
        <span className={`badge badge-${v.passed ? "pass" : "fail"}`}>
          {v.passed ? "pass" : "fail"}
        </span>
        <span className="faint num">{v.checked_rules} rules checked</span>
      </div>
      {v.findings.map((f) => (
        <div key={f.rule_id} className="stack" style={{ gap: "0.15rem" }}>
          <div className="row">
            <span className="code">{f.rule_id}</span>
            <span className="faint">{f.severity}</span>
          </div>
          <div className="faint ltr" style={{ fontSize: "var(--step--1)" }}>
            matched <span className="num">{f.matched.map((m) => `“${m}”`).join(", ")}</span>
          </div>
          <div className="faint ltr">
            {f.source_code} — {f.clause}
            {!f.clause_verified && <span className="chip chip-label" style={{ marginInlineStart: "0.4rem" }}>clause unverified</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

export function CreativesView({ data }: { data: CreativesResponse }) {
  const slots = [...new Set(data.creatives.map((c) => c.slot))];
  const [lang, setLang] = useState("en");
  const shown = data.creatives.filter((c) => c.lang === lang);

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile label="Variants" value={String(data.count)} detail="3 slots × 3 languages" />
        <StatTile
          label="Compliant"
          value={`${data.passing}/${data.count}`}
          detail="checked against the eleven brand rules"
          token={data.passing > 0 ? "--pass-text" : "--fail-text"}
        />
        <StatTile label="Reproducible" value="Yes" detail="seeded; identical bytes every run" />
        <StatTile label="Composed from" value="sidra.yaml" detail="brand palette, type, products, prices" />
      </div>

      <div className="row" style={{ justifyContent: "space-between" }}>
        <p className="note" style={{ margin: 0 }}>
          The Arabic variant is <em>written</em> in Arabic in the brand kit, not machine-translated
          from the English. A translated superlative is still a superlative, and SIDRA&rsquo;s voice
          rule is to say the specific thing.
        </p>
        <div role="group" aria-label="Language" className="row" style={{ gap: "0.25rem" }}>
          {["en", "ar", "hi"].map((l) => (
            <button key={l} type="button" className="btn" aria-pressed={lang === l}
                    onClick={() => setLang(l)} style={{ padding: "0.25rem 0.6rem", fontSize: "0.72rem" }}>
              {LANG_LABEL[l]}
            </button>
          ))}
        </div>
      </div>

      <div className="split">
        {shown.map((item) => (
          <article key={`${item.slot}-${item.lang}`} className="card stack" style={{ gap: "0.8rem" }}>
            <div className="between">
              <span className="code">{item.slot}</span>
              <span className="faint num">{item.zone} · {item.daypart}</span>
            </div>

            {/* The composed ad, at its real aspect ratio. */}
            <div
              style={{ borderRadius: "var(--radius)", overflow: "hidden", border: "1px solid var(--border)" }}
              dangerouslySetInnerHTML={{ __html: item.svg.replace(/width="\d+" height="\d+"/, 'width="100%"') }}
            />

            <div className="stack" style={{ gap: "0.3rem" }}>
              <div className="between faint">
                <span>panel mean</span>
                <span className="num">{item.panel.mean.toFixed(2)} / 10</span>
              </div>
              <div style={{ height: 6, background: "var(--surface-hover)", borderRadius: 3 }}>
                <div style={{ width: `${item.panel.mean * 10}%`, height: "100%",
                              background: "var(--sig-forecast)", borderRadius: 3 }} />
              </div>
              <span className="faint">spread {item.panel.spread.toFixed(2)} across five personas</span>
            </div>

            <Verdict item={item} />
            <span className="faint num">seed {item.seed}</span>
          </article>
        ))}
      </div>

      <p className="note">
        Slots: {slots.join(", ")}. One of them breaks the rules deliberately — a compliance tab
        that never catches anything is decoration, and a gold set needs a positive case.
      </p>
    </div>
  );
}
