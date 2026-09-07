"use client";

import { useState } from "react";
import { StatTile } from "@/components/charts/Chart";
import { API_BASE, type GoldResponse, type RulesResponse } from "@/lib/api";

const SEVERITY_TOKEN: Record<string, string> = {
  critical: "--heat-5",
  high: "--heat-4",
  medium: "--heat-3",
  low: "--heat-1",
};

export function ComplianceView({ rules, gold }: { rules: RulesResponse; gold: GoldResponse }) {
  const [text, setText] = useState("");
  const [result, setResult] = useState<{ passed: boolean; findings: { rule_id: string; severity: string; matched: string[]; clause: string; source_code: string }[] } | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    if (!text.trim()) return;
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/compliance/check?text=${encodeURIComponent(text)}`);
      setResult(await res.json());
    } catch {
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  const verified = rules.rules.filter((r) => r.clause_verified).length;

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile
          label="Recall on the gold set"
          value={`${(gold.recall * 100).toFixed(0)}%`}
          detail={`target ${(gold.target_recall * 100).toFixed(0)}% · ${gold.violations} violations`}
          token={gold.recall >= gold.target_recall ? "--pass-text" : "--fail-text"}
        />
        <StatTile
          label="Precision"
          value={`${(gold.precision * 100).toFixed(0)}%`}
          detail={`${gold.clean} clean cases, deliberately adversarial`}
          token="--pass-text"
        />
        <StatTile label="Rules" value={String(rules.rules.length)} detail={`${verified} with a verbatim clause`} />
        <StatTile label="Decision" value="Regex" detail="no model in the verdict path" />
      </div>

      <p className="note ltr">{rules.note}</p>

      <section className="stack">
        <h2 className="h3">Check a line of copy</h2>
        <p className="note">
          The same engine the Creatives tab uses. Try &ldquo;our best sugar-free detox latte&rdquo;,
          or &ldquo;was AED 32, now AED 24, until 30 September&rdquo; — the second is a discount
          claim with its terms stated, which is permitted.
        </p>
        <div className="row" style={{ gap: "0.5rem", alignItems: "stretch" }}>
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && run()}
            placeholder="Type a headline or a body line"
            aria-label="Copy to check"
            style={{
              flex: 1, minWidth: 0, font: "inherit", fontSize: "var(--step--1)",
              padding: "0.5rem 0.7rem", borderRadius: "var(--radius)",
              border: "1px solid var(--border-strong)", background: "var(--surface)",
              color: "var(--text)",
            }}
          />
          <button type="button" className="btn" onClick={run} disabled={busy}>
            {busy ? "Checking" : "Check"}
          </button>
        </div>
        {result && (
          <div className="card stack" style={{ gap: "0.5rem" }}>
            <div className="row">
              <span className={`badge badge-${result.passed ? "pass" : "fail"}`}>
                {result.passed ? "pass" : "fail"}
              </span>
              <span className="faint">{result.findings.length} finding(s)</span>
            </div>
            {result.findings.map((f) => (
              <div key={f.rule_id} className="stack" style={{ gap: "0.15rem" }}>
                <div className="row">
                  <span className="code">{f.rule_id}</span>
                  <span className="faint">{f.severity}</span>
                  <span className="faint num">{f.matched.map((m) => `“${m}”`).join(", ")}</span>
                </div>
                <div className="faint ltr">{f.source_code} — {f.clause}</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="stack">
        <h2 className="h3">The rule set</h2>
        <div className="stack" style={{ gap: "1rem" }}>
          {rules.rules.map((r) => (
            <article key={r.id} className="card stack" style={{ gap: "0.4rem" }}>
              <div className="between">
                <div className="row">
                  <span className="code">{r.id}</span>
                  <span
                    className="chip chip-dot"
                    style={{ ["--dot" as string]: `var(${SEVERITY_TOKEN[r.severity]})` }}
                  >
                    {r.severity}
                  </span>
                  <span className="chip">{r.rule_type}</span>
                </div>
                <span className="faint">{r.family}</span>
              </div>
              <p className="body ltr" style={{ margin: 0, fontSize: "var(--step--1)" }}>{r.why}</p>
              {r.patterns.length > 0 && (
                <p className="faint num" style={{ margin: 0, wordBreak: "break-word" }}>
                  {r.patterns.slice(0, 6).join("  ·  ")}
                  {r.patterns.length > 6 && ` … +${r.patterns.length - 6}`}
                </p>
              )}
              <div className="row">
                <a href={r.source_url} target="_blank" rel="noopener noreferrer" className="faint">
                  {r.source}
                </a>
                <span className="faint">— {r.clause}</span>
                {r.clause_verified ? (
                  <span className="badge badge-pass">verbatim</span>
                ) : (
                  <span className="chip chip-label">clause unverified</span>
                )}
              </div>
              {r.clause_quote && (
                <p className="note ltr" style={{ margin: 0 }}>&ldquo;{r.clause_quote}&rdquo;</p>
              )}
            </article>
          ))}
        </div>
      </section>

      <section className="stack">
        <h2 className="h3">Why precision is reported next to recall</h2>
        <p className="note">
          A rule that flags everything has perfect recall and no value — a compliance tool that
          flags good copy gets switched off, and then it catches nothing at all. Half the gold set
          is clean copy chosen to trip a naive matcher: discounts with stated terms, allergen
          statements, and &ldquo;fresh&rdquo; qualified by &ldquo;baked on site&rdquo;.
        </p>
        <div className="cards">
          <StatTile label="Gold cases" value={String(gold.cases)} detail={`${gold.violations} must fire, ${gold.clean} must not`} />
          <StatTile label="F1" value={gold.f1.toFixed(2)} detail="harmonic mean of the two" />
          <StatTile label="Missed" value={String(gold.missed.length)} detail="violations not caught" token={gold.missed.length ? "--fail-text" : "--pass-text"} />
          <StatTile label="False alarms" value={String(gold.false_alarms.length)} detail="clean copy flagged" token={gold.false_alarms.length ? "--fail-text" : "--pass-text"} />
        </div>
      </section>
    </div>
  );
}
