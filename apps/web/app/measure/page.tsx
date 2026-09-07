"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.prove")} title={t("tab.measure")} lede="Incremental lift, not clicks." />
      <Scaffold
        phase="B"
        will={[
          "Synthetic control per promo window, built from comparable non-promo days and sites",
          "CUPED variance reduction using pre-period footfall as the covariate",
          "Lift reported with a confidence interval; an injected +20% must be recovered within 5 points",
        ]}
        from="footfall_hourly and the Phase B plan"
      />
    </div>
  );
}
