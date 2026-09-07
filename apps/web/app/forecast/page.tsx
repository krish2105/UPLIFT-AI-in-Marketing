"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.plan")} title={t("tab.forecast")} lede="Eight weeks of demand per site, with the drivers that moved it." />
      <Scaffold
        phase="B"
        will={[
          "Gradient-boosted hourly forecast per site, 56 days ahead, with an 80% prediction interval",
          "Win rate against a seasonal-naive baseline, reported per week — the model is not used if it loses",
          "Driver attribution: event proximity, apparent temperature against outdoor share, Ramadan, school break",
        ]}
        from="footfall_hourly joined to weather_hourly, calendar_days and events"
      />
    </div>
  );
}
