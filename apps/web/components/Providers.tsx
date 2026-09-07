"use client";

import { ThemeProvider } from "next-themes";

/* next-themes writes `data-theme` on <html>, which is exactly what
 * styles/tokens.css keys its two registers on. `enableSystem` makes "system" a
 * real third state rather than a synonym for one of the other two: with no
 * explicit choice no attribute is written at all, and the prefers-color-scheme
 * block in tokens.css takes over.
 *
 * disableTransitionOnChange stops every colour on the page animating at once
 * when the register flips, which reads as a glitch rather than as a
 * transition.
 */
export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="data-theme" defaultTheme="system" enableSystem disableTransitionOnChange>
      {children}
    </ThemeProvider>
  );
}
