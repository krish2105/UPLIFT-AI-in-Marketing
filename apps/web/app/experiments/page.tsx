"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.prove")} title={t("tab.experiments")} lede="How a promotion is designed so its effect can be measured at all." />
      <Scaffold
        phase="B"
        will={[
          "Holdout design: which sites and which days are withheld, and why",
          "Minimum detectable effect for a given window and budget",
          "Pre-registration of the metric, so the analysis cannot be chosen after the result",
        ]}
        from="the Phase B uplift model and the site history"
      />
    </div>
  );
}
