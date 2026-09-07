"use client";

/* Locale as client state.
 *
 * The language choice sets `lang` and `dir` on <html>, so Arabic mirrors the
 * whole document rather than only the strings — the nav, the rails, the
 * scroll direction. It persists per reader in localStorage; there is no server
 * component to it because nothing about it needs to be, and a cookie round trip
 * to flip a direction would be slower than the flip.
 */

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { DIR, type Locale, t as translate } from "@/lib/i18n";

const KEY = "mawsim.locale";

type Ctx = { locale: Locale; setLocale: (l: Locale) => void; t: (key: string) => string };
const LocaleContext = createContext<Ctx>({ locale: "en", setLocale: () => {}, t: (k) => k });

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY) as Locale | null;
      if (saved && saved in DIR) setLocaleState(saved);
    } catch {
      // A private window or blocked storage is not an error; English stands.
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = DIR[locale];
  }, [locale]);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    try {
      localStorage.setItem(KEY, l);
    } catch {
      // Preference not persisted; the session still switches.
    }
  }, []);

  const t = useCallback((key: string) => translate(locale, key), [locale]);

  return <LocaleContext.Provider value={{ locale, setLocale, t }}>{children}</LocaleContext.Provider>;
}

export const useLocale = () => useContext(LocaleContext);
