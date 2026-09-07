import { readFileSync, existsSync, statSync } from "node:fs";
import { join } from "node:path";
import { PageHead } from "@/components/PageHead";
import { StatTile } from "@/components/charts/Chart";

/* The Report tab reads the generated artefact from disk.
 *
 * It does not re-derive anything: the report is built by scripts/build_report.py
 * out of docs/results/, and this shows what that produced. If the two ever
 * disagreed it would mean the report on disk is stale, which is exactly what a
 * reader should be able to see.
 */
const ROOT = join(process.cwd(), "..", "..");
const REPORT = join(ROOT, "docs", "artefacts", "AI208_MAWSIM_report.md");

export default function ReportPage() {
  const present = existsSync(REPORT);
  const md = present ? readFileSync(REPORT, "utf8") : "";
  const built = present ? statSync(REPORT).mtime.toISOString().slice(0, 16).replace("T", " ") : null;

  const sections = md
    .split(/^## /m)
    .slice(1)
    .map((s) => {
      const [head, ...rest] = s.split("\n");
      return { head: head.trim(), body: rest.join("\n").trim() };
    });

  return (
    <div className="page">
      <PageHead
        eyebrow="Prove"
        title="Report"
        lede="The coursework artefact, generated from docs/results/. Every figure in it was read out of a measurement file; none was typed."
      />

      {!present ? (
        <div className="scaffold stack" style={{ gap: "0.6rem" }}>
          <span className="chip chip-label">not generated</span>
          <p className="body" style={{ margin: 0 }}>
            Run <span className="num">uv run python scripts/build_report.py</span>. It refuses
            rather than omitting a section whose result is missing — a report with a hole in it
            is recoverable, one that silently dropped its weakest result is not.
          </p>
        </div>
      ) : (
        <>
          <div className="cards" style={{ marginBottom: "1.6rem" }}>
            <StatTile label="Sections" value={String(sections.length)} detail="all generated" />
            <StatTile label="Built" value={built ?? "—"} detail="from docs/results/" />
            <StatTile label="Figures typed by hand" value="0" detail="the generator reads, it does not author" token="--pass-text" />
            <StatTile label="Formats" value="md · docx" detail="docs/artefacts/" />
          </div>

          <p className="note" style={{ marginBottom: "1.6rem" }}>
            The generator raises if a results file it quotes is missing, rather than dropping the
            section. The placeholder scan runs before it in <span className="num">make check</span>,
            so an artefact cannot be produced while any published document still contains a
            placeholder.
          </p>

          <div className="stack">
            {sections.map((s) => (
              <article key={s.head} className="card stack" style={{ gap: "0.5rem" }}>
                <h2 className="h3">{s.head}</h2>
                <pre
                  className="ltr"
                  style={{
                    margin: 0,
                    whiteSpace: "pre-wrap",
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.72rem",
                    lineHeight: 1.6,
                    color: "var(--text-muted)",
                    overflowX: "auto",
                  }}
                >
                  {s.body.slice(0, 1400)}
                  {s.body.length > 1400 ? "\n…" : ""}
                </pre>
              </article>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
