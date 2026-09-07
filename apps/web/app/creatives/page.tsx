import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { CreativesView } from "@/components/views/CreativesView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function CreativesPage() {
  const c = await tryFetch(() => api.creatives("square"));
  if ("error" in c) return <ApiDown eyebrow="Make" title="Creatives" detail={c.error} />;
  return (
    <div className="page">
      <PageHead
        eyebrow="Make"
        title="Creatives"
        lede="Three slots, three languages, composed from the brand kit. Every variant renders identically every time, because the panel that scores it can only mean something if the thing being scored is stable."
      />
      <CreativesView data={c.data} />
    </div>
  );
}
