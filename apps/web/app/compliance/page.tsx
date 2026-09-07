"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.make")} title={t("tab.compliance")} lede="Every claim checked against a cited rule, before anything leaves the building." />
      <Scaffold
        phase="C"
        will={[
          "The eleven rules in the brand kit, enforced with the clause each comes from",
          "Retrieval-grounded verdicts over Codex CXG 23-1997, CXG 2-1985, MoEC and Dubai Municipality guidance",
          "qwen2.5vl reads the rendered creative back and re-runs the rules on the visible text",
          "Recall measured on a 40-case gold set; the target is 0.9",
        ]}
        from="the brand kit's rule set and the Phase C corpus"
      />
    </div>
  );
}
