"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.prove")} title={t("tab.report")} lede="The coursework artefacts, generated after the placeholder scan is empty." />
      <Scaffold
        phase="E"
        will={[
          "AI208_MAWSIM_report.docx, built from docs/results/ with every figure traced",
          "Deck outline, notebook, fifteen viva questions and a three-minute demo script",
          "Nothing is generated while any published document still contains a placeholder",
        ]}
        from="docs/results/ and the measured outcomes of Phases B to D"
      />
    </div>
  );
}
