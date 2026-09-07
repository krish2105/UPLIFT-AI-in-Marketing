import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { StatTile } from "@/components/charts/Chart";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function CrewPage() {
  const c = await tryFetch(api.crew);
  if ("error" in c) return <ApiDown eyebrow="System" title="Crew" detail={c.error} />;
  const { crew, side_effect_free, claim, publishing } = c.data;

  return (
    <div className="page">
      <PageHead
        eyebrow="System"
        title="Crew"
        lede="Seven agents, their tools, and the one column that carries the whole safety argument."
      />

      <div className="cards" style={{ marginBottom: "1.6rem" }}>
        <StatTile label="Agents" value={String(crew.length)} detail="each with a stated output" />
        <StatTile
          label="Side effects"
          value={side_effect_free ? "None" : "SOME"}
          detail="on every row, asserted by a test"
          token={side_effect_free ? "--pass-text" : "--fail-text"}
        />
        <StatTile label="Tools that reach outside" value="0" detail="no HTTP, no mail, no scheduler" token="--pass-text" />
        <StatTile label="Publishing" value="Human" detail="taken outside this application" />
      </div>

      <p className="note ltr" style={{ marginBottom: "1.6rem" }}>{claim}</p>

      <div className="scroll-x">
        <table className="data">
          <thead>
            <tr><th>agent</th><th>phase</th><th>tools</th><th>reads</th><th>output</th><th>side effects</th></tr>
          </thead>
          <tbody>
            {crew.map((a) => (
              <tr key={a.agent}>
                <td><strong>{a.agent}</strong></td>
                <td className="num">{a.phase}</td>
                <td className="num">{a.tools.join(", ")}</td>
                <td className="faint ltr">{a.reads}</td>
                <td className="ltr">{a.output}</td>
                <td>
                  <span className="badge badge-pass">{a.side_effects}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <section className="stack" style={{ marginTop: "1.8rem" }}>
        <h2 className="h3">What each one is for</h2>
        <div className="split">
          {crew.map((a) => (
            <article key={a.agent} className="card stack" style={{ gap: "0.35rem" }}>
              <div className="between">
                <span className="code">{a.agent}</span>
                <span className="chip">phase {a.phase}</span>
              </div>
              <p className="faint ltr" style={{ margin: 0 }}>{a.note}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="stack" style={{ marginTop: "1.8rem" }}>
        <h2 className="h3">Publishing</h2>
        <p className="note ltr">{publishing}</p>
      </section>
    </div>
  );
}
