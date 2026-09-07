"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.plan")} title={t("tab.plan")} lede="A promo calendar sized to the forecast's lower bound, and a budget split." />
      <Scaffold
        phase="B"
        will={[
          "Calendar builder over the 56-day horizon, with event and weather bands",
          "Budget allocator over channel x daypart — 5 channels, 3 dayparts, 15 cells on a simplex",
          "What-if sliders: allocation always sums to budget and is monotone in ROI",
        ]}
        from="the Phase B forecast and convex response curves per cell"
      />
    </div>
  );
}
