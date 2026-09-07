"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.system")} title={t("tab.ask")} lede="Questions answered from the corpus, with citations, in three languages." />
      <Scaffold
        phase="C"
        will={[
          "Hybrid retrieval — BM25 and vector, fused — over the brand kit, the regulations and the event listings",
          "Every factual sentence carries a citation; an uncited sentence is not returned",
          "bge-m3 locally, MiniLM deployed; see docs/models.md for why",
        ]}
        from="the Phase C corpus and the provider chain"
      />
    </div>
  );
}
