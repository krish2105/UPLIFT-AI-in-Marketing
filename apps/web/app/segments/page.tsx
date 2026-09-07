import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { SegmentsView } from "@/components/views/SegmentsView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function SegmentsPage() {
  const s = await tryFetch(api.segments);
  if ("error" in s) return <ApiDown eyebrow="Plan" title="Segments" detail={s.error} />;
  return (
    <div className="page">
      <PageHead
        eyebrow="Plan"
        title="Segments"
        lede="Who the customers are, in groups a shift manager can name and act on."
      />
      <SegmentsView data={s.data} />
    </div>
  );
}
