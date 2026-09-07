"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.make")} title={t("tab.panel")} lede="A persona panel scores the variants. It complements customer research; it does not replace it." />
      <Scaffold
        phase="C"
        will={[
          "Five personas grounded in a labelled corpus, deterministic under a seed",
          "Scores with a confidence, feeding back into the planner",
          "Every persona publishes what it over- and under-weights",
        ]}
        from="a seeded persona set and the Phase C retrieval layer"
      />
    </div>
  );
}
