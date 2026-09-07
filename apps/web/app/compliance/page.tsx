import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { ComplianceView } from "@/components/views/ComplianceView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function CompliancePage() {
  const [r, g] = await Promise.all([tryFetch(api.rules), tryFetch(api.gold)]);
  if ("error" in r || "error" in g) {
    return <ApiDown eyebrow="Make" title="Compliance" detail={"error" in r ? r.error : ""} />;
  }
  return (
    <div className="page">
      <PageHead
        eyebrow="Make"
        title="Compliance"
        lede="Eleven rules, each naming the document it came from. Deterministic, because a rule engine whose verdict depends on a model's mood cannot be audited."
      />
      <ComplianceView rules={r.data} gold={g.data} />
    </div>
  );
}
