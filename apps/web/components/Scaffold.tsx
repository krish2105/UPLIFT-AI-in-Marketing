"use client";

import { useLocale } from "@/components/LocaleProvider";

/* An honest empty state.
 *
 * The alternative — filling a tab with plausible-looking placeholder numbers
 * until the real thing arrives — is how a demo starts lying. This says what the
 * page will hold, which phase builds it, and what it will be built from, and
 * shows nothing that could be mistaken for a result.
 */
export function Scaffold({
  phase,
  will,
  from,
}: {
  phase: string;
  will: string[];
  from: string;
}) {
  const { t } = useLocale();
  return (
    <div className="scaffold stack" style={{ gap: "0.9rem" }}>
      <div className="row" style={{ gap: "0.6rem" }}>
        <span className="chip chip-label">{t("scaffold.title")}</span>
        <span className="chip">{t("scaffold.phase")} {phase}</span>
      </div>
      <ul className="stack" style={{ gap: "0.4rem", margin: 0, paddingInlineStart: "1.1rem" }}>
        {will.map((w) => <li key={w} style={{ fontSize: "var(--step--1)" }}>{w}</li>)}
      </ul>
      <p className="faint" style={{ margin: 0 }}>Built from: {from}</p>
      <p className="faint" style={{ margin: 0 }}>{t("scaffold.why")}</p>
    </div>
  );
}
