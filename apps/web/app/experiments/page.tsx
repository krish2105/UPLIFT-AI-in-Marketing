import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { ExperimentsView } from "@/components/views/ExperimentsView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function ExperimentsPage() {
  const e = await tryFetch(() => api.experiments("DXB-MAR", 14));
  if ("error" in e) return <ApiDown eyebrow="Prove" title="Experiments" detail={e.error} />;
  return (
    <div className="page">
      <PageHead
        eyebrow="Prove"
        title="Experiments"
        lede="Most promotions are unmeasurable by construction: they run everywhere at once, so there is nothing to compare against. Both the holdout and the metric are decided before the promotion, or not at all."
      />
      <ExperimentsView data={e.data} />
    </div>
  );
}
