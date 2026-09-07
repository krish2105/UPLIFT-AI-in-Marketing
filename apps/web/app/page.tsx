import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { SeasonView } from "@/components/views/SeasonView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function SeasonPage() {
  const t = await tryFetch(() => api.terrain(56));
  if ("error" in t) return <ApiDown eyebrow="Plan" title="Season" detail={t.error} />;
  return (
    <div className="page">
      <PageHead
        eyebrow="Plan"
        title="Season"
        lede="Eight weeks of demand across four sites, with the events that cross them and the weather that moves them. Every block wears its prediction interval, because extrusion reads as fact."
      />
      <SeasonView data={t.data} />
    </div>
  );
}
