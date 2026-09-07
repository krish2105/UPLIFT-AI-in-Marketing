"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.make")} title={t("tab.creatives")} lede="Three variants per slot, in three languages, composed from the brand kit." />
      <Scaffold
        phase="C"
        will={[
          "Deterministic brand-accurate compositions at three sizes, EN/AR/HI with correct RTL mirroring",
          "Seeded, so the panel scores are reproducible",
          "A free image tier behind a flag, cached to disk, degrading to the composition",
        ]}
        from="data/brand/sidra.yaml and the Phase B plan"
      />
    </div>
  );
}
