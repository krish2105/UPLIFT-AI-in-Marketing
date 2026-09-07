"use client";

import { LOCALES, LOCALE_NAME } from "@/lib/i18n";
import { useLocale } from "@/components/LocaleProvider";

/** Each language is written in its own script. A dropdown listing "Arabic" in
 *  English asks a reader to find their language in a language they may not
 *  read. */
export function LangToggle() {
  const { locale, setLocale, t } = useLocale();
  return (
    <div role="group" aria-label={t("lang.label")} style={{ display: "inline-flex", gap: "0.25rem" }}>
      {LOCALES.map((l) => (
        <button
          key={l}
          type="button"
          className="btn"
          lang={l}
          aria-pressed={locale === l}
          onClick={() => setLocale(l)}
          style={{ padding: "0.28rem 0.6rem", fontSize: "0.72rem" }}
        >
          {LOCALE_NAME[l]}
        </button>
      ))}
    </div>
  );
}
