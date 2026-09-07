import { PageHead } from "@/components/PageHead";
import { api, tryFetch } from "@/lib/api";

/* The Brand tab: the fictional brand, stated as such, with the rules the
 * Compliance agent actually enforces. Reads the same YAML the guideline PDF is
 * generated from, so this page and that document cannot disagree. */
export const revalidate = 60;

export default async function BrandPage() {
  const result = await tryFetch(api.zones);

  if ("error" in result) {
    return (
      <div className="page">
        <PageHead eyebrow="Make" title="Brand" />
        <div className="scaffold"><span className="chip chip-label">API unreachable</span></div>
      </div>
    );
  }

  const { brand, zones } = result.data;

  return (
    <div className="page">
      <PageHead
        eyebrow="Make"
        title="Brand"
        lede="The brand every forecast, promotion, creative and compliance verdict in this application refers to."
      />

      <div className="card stack" style={{ gap: "0.6rem", marginBottom: "1.8rem" }}>
        <div className="row">
          <span className="chip chip-label">fictional</span>
          <span className="code">{brand.name}</span>
          <span lang="ar" dir="rtl" style={{ fontSize: "var(--step-1)" }}>{brand.name_ar}</span>
        </div>
        <p className="body ltr" style={{ margin: 0 }}>{brand.disclaimer}</p>
      </div>

      <section className="stack" style={{ marginBottom: "1.8rem" }}>
        <h2 className="h3">Four sites, deliberately unalike</h2>
        <p className="note">
          Al Barsha is fully enclosed and Marina Walk is more than half outdoors, so the same
          weather moves them in opposite directions. That is why demand is forecast per site
          rather than per brand — and the simulator derives each site&rsquo;s weather elasticity
          from these seat counts rather than hardcoding it.
        </p>
        <div className="split">
          {zones.map((z) => (
            <article key={z.code} className="card stack" style={{ gap: "0.45rem" }}>
              <div className="between">
                <span className="code">{z.code}</span>
                <span className="faint num">{z.opens} – {z.closes}</span>
              </div>
              <div>
                <div className="h3">{z.name}</div>
                <div className="faint" lang="ar" dir="rtl">{z.name_ar}</div>
              </div>
              <p className="faint ltr" style={{ margin: 0 }}>{z.character}</p>

              {/* Outdoor share drives the elasticity, so it is drawn rather than
                  printed — a bar makes the comparison across sites immediate. */}
              <div className="stack" style={{ gap: "0.25rem" }}>
                <div className="between faint">
                  <span>outdoor seating</span>
                  <span className="num">{Math.round(z.outdoor_share * 100)}%</span>
                </div>
                <div style={{ display: "flex", gap: 2, height: 8 }}>
                  <div style={{ width: `${z.outdoor_share * 100}%`, background: "var(--accent)", borderRadius: 4 }} />
                  <div style={{ flex: 1, background: "var(--surface-hover)", borderRadius: 4 }} />
                </div>
                <span className="faint num">
                  {z.outdoor_seats} outdoor · {z.seats} indoor
                </span>
              </div>

              <p className="faint ltr" style={{ margin: 0 }}>{z.demand_notes}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="stack">
        <h2 className="h3">The guidelines</h2>
        <p className="note">
          The brand-guideline PDF is generated from <code>data/brand/sidra.yaml</code>, the same
          file the Compliance agent enforces its rules from, so the document a reviewer reads and
          the rules the system applies cannot drift apart. Where a rule cites a clause that has
          not yet been read verbatim from its source, the PDF prints
          &ldquo;clause unverified&rdquo; rather than implying otherwise.
        </p>
        <p className="faint">
          The eleven rules, their sources and their verification state are rendered on the
          Compliance tab once Phase C lands.
        </p>
      </section>
    </div>
  );
}
