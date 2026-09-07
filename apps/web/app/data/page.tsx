import { PageHead } from "@/components/PageHead";
import { api, tryFetch } from "@/lib/api";

/* The Data tab: provenance, live.
 *
 * Server-rendered, because the whole point is that it reflects the database as
 * it is now rather than what someone typed into a fixture. If the API is
 * asleep — the free instance spins down after 15 minutes — the page says so
 * plainly instead of showing an error overlay.
 */
export const revalidate = 60;

const LABEL_ORDER = ["observed", "curated", "simulated", "sample"];

export default async function DataPage() {
  const result = await tryFetch(api.freshness);

  if ("error" in result) {
    return (
      <div className="page">
        <PageHead eyebrow="System" title="Data" />
        <div className="scaffold stack" style={{ gap: "0.6rem" }}>
          <span className="chip chip-label">API unreachable</span>
          <p className="body" style={{ margin: 0 }}>
            The API did not answer. The deployed instance runs on a free tier and sleeps after
            fifteen minutes idle, so the first request after a quiet period takes about a minute.
          </p>
          <p className="faint" style={{ margin: 0 }}>{result.error}</p>
        </div>
      </div>
    );
  }

  const f = result.data;
  const sorted = [...f.datasets].sort(
    (a, b) => LABEL_ORDER.indexOf(a.label) - LABEL_ORDER.indexOf(b.label),
  );

  return (
    <div className="page">
      <PageHead
        eyebrow="System"
        title="Data"
        lede="Every dataset, what it is, where it came from, and how much of it there is. Read live from the database rather than stored, because a stored row count goes stale the moment a pipeline runs."
      />

      <div className="cards" style={{ marginBottom: "1.6rem" }}>
        <div className="card stack" style={{ gap: "0.25rem" }}>
          <span className="eyebrow" style={{ margin: 0 }}>Rows loaded</span>
          <span className="num" style={{ fontSize: "var(--step-2)" }}>
            {f.totals.rows.toLocaleString("en-GB")}
          </span>
          <span className="faint">across {f.totals.datasets} datasets</span>
        </div>
        {LABEL_ORDER.filter((l) => f.totals.by_label[l]).map((l) => (
          <div key={l} className="card stack" style={{ gap: "0.25rem" }}>
            <span className="eyebrow" style={{ margin: 0 }}>{l}</span>
            <span className="num" style={{ fontSize: "var(--step-2)" }}>{f.totals.by_label[l]}</span>
            <span className="faint">
              {l === "observed" ? "fetched, unmodified"
                : l === "curated" ? "assembled here"
                : l === "simulated" ? "generated, no counterpart"
                : "a stand-in export"}
            </span>
          </div>
        ))}
      </div>

      <p className="note ltr" style={{ marginBottom: "1.4rem" }}>{f.standing_note}</p>

      <div className="stack-l">
        {sorted.map((d) => (
          <article key={d.key} className="card stack" style={{ gap: "0.6rem" }}>
            <div className="between" style={{ alignItems: "flex-start" }}>
              <div className="stack" style={{ gap: "0.2rem" }}>
                <div className="row">
                  <span className="chip chip-label">{d.label}</span>
                  <span className="code">{d.table}</span>
                </div>
                <h2 className="h3">{d.title}</h2>
              </div>
              <div style={{ textAlign: "end" }}>
                <div className="num" style={{ fontSize: "var(--step-1)" }}>
                  {d.rows.toLocaleString("en-GB")}
                </div>
                <div className="faint num">
                  {d.span ? `${d.span[0].slice(0, 10)} → ${d.span[1].slice(0, 10)}` : "no rows"}
                </div>
              </div>
            </div>

            <p className="body ltr" style={{ margin: 0, fontSize: "var(--step--1)" }}>{d.description}</p>
            <p className="note ltr" style={{ margin: 0 }}>{d.caveat}</p>

            <div className="scroll-x">
              <table className="data">
                <tbody>
                  <tr>
                    <th style={{ width: "8rem" }}>Source</th>
                    <td>
                      <a href={d.source_url} target="_blank" rel="noopener noreferrer">{d.source_name}</a>
                    </td>
                  </tr>
                  <tr><th>Licence</th><td className="ltr">{d.licence}</td></tr>
                  <tr><th>Verified</th><td className="num">{d.verified}</td></tr>
                  <tr><th>Built by</th><td className="num">{d.built_by}</td></tr>
                </tbody>
              </table>
            </div>
          </article>
        ))}
      </div>

      <p className="faint" style={{ marginTop: "1.4rem" }}>
        Generated {f.generated_at}. Full provenance, including the sources that refused, is in{" "}
        <code>docs/datasets.md</code>.
      </p>
    </div>
  );
}
