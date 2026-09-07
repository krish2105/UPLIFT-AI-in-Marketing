"use client";

import { useLocale } from "@/components/LocaleProvider";

/** The standing note. Present on every page, in the reader's language, because
 *  a reader who lands deep on the Measure tab never saw the home page. */
export function Disclaimer() {
  const { t } = useLocale();
  return (
    <footer className="footer">
      <p className="faint" style={{ margin: 0 }}>
        <strong style={{ color: "var(--text-muted)" }}>{t("brand.fictional")}</strong>{" "}
        {t("brand.simulated")} {t("app.course")}
      </p>
    </footer>
  );
}
