import { PageHead } from "@/components/PageHead";

/** The honest empty state. Shown instead of a chart drawn from nothing. */
export function ApiDown({ eyebrow, title, detail }: { eyebrow: string; title: string; detail?: string }) {
  return (
    <div className="page">
      <PageHead eyebrow={eyebrow} title={title} />
      <div className="scaffold stack" style={{ gap: "0.6rem" }}>
        <span className="chip chip-label">API unreachable</span>
        <p className="body" style={{ margin: 0 }}>
          The API did not answer. It runs on a free instance that sleeps after fifteen minutes
          idle, so the first request after a quiet period takes about a minute. Nothing is drawn
          here in the meantime, because a chart built from no data is worse than no chart.
        </p>
        {detail && <p className="faint ltr" style={{ margin: 0 }}>{detail}</p>}
      </div>
    </div>
  );
}
