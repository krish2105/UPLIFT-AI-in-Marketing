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
  const { summary, controls, note, red_team: red } = s.data;

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

      {red && (
        <section className="stack" style={{ marginBottom: "1.8rem" }}>
          <h2 className="h3">What happened when the claims were attacked</h2>
          <div className="cards">
            <StatTile
              label="Attacks run"
              value={String(red.cases)}
              detail="prompt injection, evasion, forged roles, traversal"
            />
            <StatTile
              label="Held"
              value={`${red.held}/${red.cases}`}
              detail={
                red.unaccepted_breaks > 0
                  ? `${red.unaccepted_breaks} unexplained break`
                  : red.accepted_breaks > 0
                    ? `${red.accepted_breaks} break, stated below`
                    : "no attack achieved its objective"
              }
              token={red.unaccepted_breaks > 0 ? "--fail-text" : "--pass-text"}
            />
            <StatTile label="Controls probed" value={String(Object.keys(red.by_control).length)} detail="each case names the row it tests" />
            <StatTile label="Last run" value={red.generated_at.slice(0, 10)} detail="inside make check" />
          </div>
          <p className="note ltr">{red.what_a_pass_means}</p>
          <p className="note ltr">
            <strong>Known limitation. </strong>{red.known_limitation}
          </p>
          <div className="scroll-x">
            <table className="data">
              <thead>
                <tr><th>case</th><th>control</th><th>attack</th><th>objective</th><th>result</th></tr>
              </thead>
              <tbody>
                {red.results.map((c) => (
                  <tr key={c.id}>
                    <td className="num">{c.id}</td>
                    <td className="num">{c.control}</td>
                    <td className="ltr" style={{ fontSize: "var(--step--1)" }}>{c.attack}</td>
                    <td className="faint ltr">{c.objective}</td>
                    <td>
                      {/* Three states, not two. An attack that worked and is
                          carried as a stated limitation is neither a pass nor a
                          silent failure, and flattening it into either would
                          hide the one row worth reading closely. */}
                      <span
                        className={`badge badge-${c.held ? "pass" : c.accepted ? "warn" : "fail"}`}
                      >
                        {c.held ? "held" : c.accepted ? "broke · accepted" : "broke"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

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
