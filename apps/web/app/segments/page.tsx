"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.plan")} title={t("tab.segments")} lede="Who the customers are, and how each group responds." />
      <Scaffold
        phase="B"
        will={[
          "RFM segmentation over the point-of-sale sample, with stability under bootstrap",
          "Segment-level response curves feeding the allocator",
          "Daypart and site mix per segment",
        ]}
        from="pos_baskets — a generated sample export"
      />
    </div>
  );
}
