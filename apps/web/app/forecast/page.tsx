import { PageHead } from "@/components/PageHead";
import { ApiDown } from "@/components/ApiDown";
import { ForecastView } from "@/components/views/ForecastView";
import { api, tryFetch } from "@/lib/api";

export const revalidate = 60;

export default async function ForecastPage() {
  const [f, z] = await Promise.all([
    tryFetch(() => api.forecast("?horizon=28")),
    tryFetch(api.zones),
  ]);
  if ("error" in f || "error" in z) {
    return <ApiDown eyebrow="Plan" title="Forecast" detail={"error" in f ? f.error : ""} />;
  }
  return (
    <div className="page">
      <PageHead
        eyebrow="Plan"
        title="Forecast"
        lede="Hourly demand per site, and the baseline it has to beat. A forecast that loses to “the same hour last week” is worse than no forecast, because it looks like knowledge."
      />
      <ForecastView forecast={f.data} zones={z.data.zones} />
    </div>
  );
}
