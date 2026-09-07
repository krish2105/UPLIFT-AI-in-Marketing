import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { MeasureView } from "@/components/views/MeasureView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function MeasurePage() {
  const u = await tryFetch(() => api.uplift());
  if ("error" in u) return <ApiDown eyebrow="Prove" title="Measure" detail={u.error} />;
  return (
    <div className="page">
      <PageHead
        eyebrow="Prove"
        title="Measure"
        lede="Incremental lift, not clicks. A promotion runs in a week; comparing that week to the last one attributes the weather, the school holiday and the festival two kilometres away to the promotion."
      />
      <MeasureView data={u.data} />
    </div>
  );
}
