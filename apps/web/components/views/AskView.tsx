"use client";

import { useState } from "react";
import { api, type AskResponse } from "@/lib/api";

const SUGGESTED = [
  "can we say sugar free",
  "which site is most affected by weather",
  "what is the footfall data",
  "why is the events dataset curated",
  "ما هي قواعد العلامة التجارية",
];

const KIND_LABEL: Record<string, string> = {
  rule: "compliance rule",
  voice: "brand voice",
  dataset: "dataset provenance",
  result: "measured result",
  brand: "brand kit",
};

/* Said in the reader's terms, not the retriever's. "Vector" and "BM25" describe
   how this was built; "words" and "meaning" describe what happened to their
   question. */
const MATCH_LABEL: Record<string, string> = {
  both: "words and meaning agree",
  lexical: "matched on words",
  vector: "matched on meaning",
};

export function AskView() {
  const [q, setQ] = useState("");
  const [res, setRes] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);

  async function ask(question: string) {
    if (!question.trim()) return;
    setQ(question);
    setBusy(true);
    try {
      setRes(await api.ask(question, 5));
    } catch {
      setRes(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack-l">
      <div className="row" style={{ gap: "0.5rem", alignItems: "stretch" }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask(q)}
          placeholder="Ask about the brand, the rules, the data or a result"
          aria-label="Question"
          style={{
            flex: 1, minWidth: 0, font: "inherit", fontSize: "var(--step-0)",
            padding: "0.6rem 0.8rem", borderRadius: "var(--radius)",
            border: "1px solid var(--border-strong)", background: "var(--surface)",
            color: "var(--text)",
          }}
        />
        <button type="button" className="btn" onClick={() => ask(q)} disabled={busy}>
          {busy ? "Searching" : "Ask"}
        </button>
      </div>

      <div className="row">
        {SUGGESTED.map((s) => (
          <button key={s} type="button" className="chip" onClick={() => ask(s)}
                  style={{ cursor: "pointer", background: "none" }}
                  lang={/[؀-ۿ]/.test(s) ? "ar" : "en"}>
            {s}
          </button>
        ))}
      </div>

      {res && (
        <section className="stack">
          <div className="between">
            <h2 className="h3">{res.answered ? `${res.citations.length} passages` : "No match"}</h2>
            <span className="faint num">corpus: {res.corpus_size} passages</span>
          </div>
          <p className="note ltr">{res.note}</p>

          {res.citations.map((c) => (
            <article key={c.id} className="card stack" style={{ gap: "0.35rem" }}>
              <div className="between">
                <div className="row">
                  <span className="code">[{c.rank}]</span>
                  <span className="chip">{KIND_LABEL[c.kind] ?? c.kind}</span>
                  <span className="code">{c.id}</span>
                </div>
                <span className="faint">{MATCH_LABEL[c.matched_by] ?? c.matched_by}</span>
              </div>
              <p className="body ltr" style={{ margin: 0, fontSize: "var(--step--1)" }}>{c.text}</p>
              <p className="faint ltr" style={{ margin: 0 }}>{c.source}</p>
            </article>
          ))}
        </section>
      )}

      <section className="stack">
        <h2 className="h3">Why an answer here is a list of passages</h2>
        <p className="note">
          A model that writes a paragraph over retrieved text can add a sentence the text does
          not support, and that sentence arrives wearing the same citation as the rest. Until
          Phase C adds a model that is forbidden from doing so, an answer is the passages
          themselves — less satisfying, and incapable of fabricating.
        </p>
        <p className="note">
          Retrieval is BM25 over the project&rsquo;s own corpus. It is not a placeholder: it is the
          half of a hybrid retriever that needs no model, it runs on a free instance with no
          embedder, and it makes the citation contract testable before any inference is
          involved. The A9 spike chose <span className="num">bge-m3</span> for the vector half —
          see <span className="num">docs/models.md</span>.
        </p>
      </section>
    </div>
  );
}
