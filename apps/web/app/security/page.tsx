"use client";

import { PageHead } from "@/components/PageHead";
import { Scaffold } from "@/components/Scaffold";
import { useLocale } from "@/components/LocaleProvider";

export default function Page() {
  const { t } = useLocale();
  return (
    <div className="page">
      <PageHead eyebrow={t("group.system")} title={t("tab.security")} lede="What this system refuses to do, and the evidence that it refuses." />
      <Scaffold
        phase="E"
        will={[
          "OWASP ASI scorecard with a red-team harness",
          "Prompt-injection cases run against every untrusted-content boundary",
          "RBAC bound to identity rather than to a request header",
          "The kill switch, checked before availability, quota or any network call",
        ]}
        from="the Phase E harness"
      />
    </div>
  );
}
