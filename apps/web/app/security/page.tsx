import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { StatTile } from "@/components/charts/Chart";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

const STATUS_TOKEN: Record<string, string> = {
  enforced: "--pass-text",
  partial: "--heat-3",
  "phase-e": "--text-faint",
};

export default async function SecurityPage() {
  const s = await tryFetch(api.security);
  if ("error" in s) return <ApiDown eyebrow="System" title="Security" detail={s.error} />;
  const { summary, controls, note } = s.data;

  return (
    <div className="page">
      <PageHead
        eyebrow="System"
        title="Security"
        lede="What this system cannot do, and the thing that stops it. Every row is backed by a test, a constructor that raises, or a route that does not exist."
      />

      <div className="cards" style={{ marginBottom: "1.6rem" }}>
        <StatTile label="Controls" value={String(summary.controls)} detail="OWASP agentic-system risks" />
        <StatTile
          label="Enforced in code"
          value={`${summary.enforced}/${summary.controls}`}
          detail={`${Math.round(summary.coverage * 100)}% — the rest are Phase E or stated partial`}
          token="--pass-text"
        />
        <StatTile label="Partial" value={String(summary.by_status.partial ?? 0)} detail="stated rather than hidden" token="--heat-3" />
        <StatTile label="Phase E" value={String(summary.by_status["phase-e"] ?? 0)} detail="the provider chain and its budgets" />
      </div>

      <p className="note ltr" style={{ marginBottom: "1.6rem" }}>{note}</p>

      <div className="stack">
        {controls.map((c) => (
          <article key={c.id} className="card stack" style={{ gap: "0.45rem" }}>
            <div className="between">
              <div className="row">
                <span className="code">{c.id}</span>
                <span
                  className="chip chip-dot"
                  style={{ ["--dot" as string]: `var(${STATUS_TOKEN[c.status]})` }}
                >
                  {c.status}
                </span>
              </div>
              <span className="faint">{c.risk}</span>
            </div>
            <p className="body ltr" style={{ margin: 0, fontSize: "var(--step--1)" }}>
              <strong>{c.claim}</strong>
            </p>
            <p className="faint ltr" style={{ margin: 0 }}>{c.evidence}</p>
            <p className="faint num" style={{ margin: 0, wordBreak: "break-word" }}>{c.verified_by}</p>
          </article>
        ))}
      </div>
    </div>
  );
}
