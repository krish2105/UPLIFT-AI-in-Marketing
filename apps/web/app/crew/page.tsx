"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.system")} title={t("tab.crew")} lede="Seven agents, their tools, and what none of them can do." />
      <Scaffold
        phase="C"
        will={[
          "Forecaster, Planner, Creative, Compliance, Panel, Measurer, Auditor",
          "A capability table: every agent, every tool, and its side effects — none, on every row",
          "That claim is asserted over the whole tool registry by a test, so a tool added later with a side effect fails the build",
        ]}
        from="the Phase C crew runtime"
      />
    </div>
  );
}
