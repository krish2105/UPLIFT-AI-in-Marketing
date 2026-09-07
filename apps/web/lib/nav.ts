/* Fifteen tabs in four groups.
 *
 * Fifteen flat links is a soup. The grouping is not cosmetic — it is the
 * argument the application makes: you forecast demand, you make something
 * against it, you prove whether it worked, and the system tab holds everything
 * that lets a reader check the first three.
 */

export type Tab = {
  href: string;
  key: string;
  /** Which phase builds it. A tab that is a scaffold says so on the page. */
  phase: "A" | "B" | "C" | "D" | "E";
};

export type Group = { key: string; tabs: Tab[] };

export const GROUPS: Group[] = [
  {
    key: "plan",
    tabs: [
      { href: "/", key: "season", phase: "D" },
      { href: "/forecast", key: "forecast", phase: "B" },
      { href: "/plan", key: "plan", phase: "B" },
      { href: "/segments", key: "segments", phase: "B" },
    ],
  },
  {
    key: "make",
    tabs: [
      { href: "/creatives", key: "creatives", phase: "C" },
      { href: "/brand", key: "brand", phase: "A" },
      { href: "/compliance", key: "compliance", phase: "C" },
      { href: "/panel", key: "panel", phase: "C" },
    ],
  },
  {
    key: "prove",
    tabs: [
      { href: "/measure", key: "measure", phase: "B" },
      { href: "/experiments", key: "experiments", phase: "B" },
      { href: "/report", key: "report", phase: "E" },
    ],
  },
  {
    key: "system",
    tabs: [
      { href: "/ask", key: "ask", phase: "C" },
      { href: "/crew", key: "crew", phase: "C" },
      { href: "/data", key: "data", phase: "A" },
      { href: "/security", key: "security", phase: "E" },
    ],
  },
];

export const ALL_TABS: Tab[] = GROUPS.flatMap((g) => g.tabs);
