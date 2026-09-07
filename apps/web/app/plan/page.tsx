import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { PlanView } from "@/components/views/PlanView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function PlanPage() {
  const a = await tryFetch(() => api.allocator(12000));
  if ("error" in a) return <ApiDown eyebrow="Plan" title="Plan" detail={a.error} />;
  return (
    <div className="page">
      <PageHead
        eyebrow="Plan"
        title="Plan"
        lede="Budget across five channels and three dayparts. Fifteen cells, a concave objective, and an optimum you can check rather than trust."
      />
      <PlanView initial={a.data} />
    </div>
  );
}
