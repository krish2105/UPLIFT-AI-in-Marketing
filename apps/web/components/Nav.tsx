"use client";

/* Fifteen tabs, grouped.
 *
 * The groups are the argument: forecast demand, make something against it,
 * prove whether it worked, and a system group holding everything that lets a
 * reader check the first three. Flat, fifteen links would be a soup.
 *
 * On a phone the whole strip scrolls horizontally in one row rather than
 * collapsing into a hamburger, because the reader is moving between sibling
 * views constantly and a menu that hides them costs a tap every time.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { GROUPS } from "@/lib/nav";
import { useLocale } from "@/components/LocaleProvider";

export function Nav() {
  const pathname = usePathname();
  const { t } = useLocale();

  return (
    <nav aria-label={t("a11y.nav")} className="nav scroll-x">
      <ul className="nav-groups">
        {GROUPS.map((g) => (
          <li key={g.key} className="nav-group">
            <span className="nav-group-label" aria-hidden="true">{t(`group.${g.key}`)}</span>
            <ul className="nav-tabs">
              {g.tabs.map((tab) => {
                const active = pathname === tab.href;
                return (
                  <li key={tab.href}>
                    <Link
                      href={tab.href}
                      className="nav-tab"
                      aria-current={active ? "page" : undefined}
                      data-active={active || undefined}
                    >
                      {t(`tab.${tab.key}`)}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </li>
        ))}
      </ul>
    </nav>
  );
}
