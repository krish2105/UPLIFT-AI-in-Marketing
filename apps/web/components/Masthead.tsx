"use client";

import Link from "next/link";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LangToggle } from "@/components/LangToggle";
import { Nav } from "@/components/Nav";
import { useLocale } from "@/components/LocaleProvider";

export function Masthead() {
  const { t } = useLocale();
  return (
    <header className="masthead">
      <a href="#content" className="skip">{t("a11y.skip")}</a>
      <div className="masthead-top">
        <Link href="/" className="wordmark">
          <span className="wordmark-name">{t("app.name")}</span>
          <span className="wordmark-sub">{t("app.tagline")}</span>
        </Link>
        <div className="row" style={{ gap: "0.9rem" }}>
          <LangToggle />
          <ThemeToggle />
        </div>
      </div>
      <Nav />
    </header>
  );
}
