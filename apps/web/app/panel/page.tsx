import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { PanelView } from "@/components/views/PanelView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function PanelPage() {
  const c = await tryFetch(() => api.creatives("square"));
  if ("error" in c) return <ApiDown eyebrow="Make" title="Panel" detail={c.error} />;
  return (
    <div className="page">
      <PageHead
        eyebrow="Make"
        title="Panel"
        lede="Five personas score every variant. It is a filter, not customer research — it applies a rubric someone wrote down, it does not observe a reaction."
      />
      <PanelView data={c.data} />
    </div>
  );
}
