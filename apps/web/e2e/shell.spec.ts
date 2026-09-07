import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/* The shell: fifteen routes, three languages, two registers, 360px up.
 *
 * These are the checks that would otherwise be claimed rather than verified —
 * "responsive", "accessible", "RTL" are all easy to assert and hard to mean.
 */

const ROUTES = [
  "/", "/forecast", "/plan", "/segments",
  "/creatives", "/brand", "/compliance", "/panel",
  "/measure", "/experiments", "/report",
  "/ask", "/crew", "/data", "/security",
] as const;

test.describe("every tab", () => {
  for (const route of ROUTES) {
    test(`${route} renders with the standing disclaimer`, async ({ page }) => {
      const res = await page.goto(route);
      expect(res?.status(), `${route} did not return 200`).toBe(200);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      // A reader landing deep must still see what SIDRA is. The footer carries
      // it on every route; some pages also say it in their own words, so this
      // targets the footer rather than matching text anywhere on the page.
      await expect(
        page.locator("footer.footer").getByText(/fictional brand/i),
      ).toBeVisible();
    });
  }
});

test("the nav offers all fifteen tabs in four groups", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: /sections/i });
  await expect(nav.getByRole("link")).toHaveCount(ROUTES.length);
});

test("the current tab is marked by more than colour", async ({ page }) => {
  await page.goto("/data");
  const current = page.locator('[aria-current="page"]');
  await expect(current).toHaveCount(1);
  await expect(current).toHaveText(/data/i);
  // aria-current is the machine-readable half; weight and a border are the
  // visible half, so identity never rests on hue alone.
  await expect(current).toHaveCSS("font-weight", "600");
});

test.describe("theme", () => {
  test("a chosen register survives a reload", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Night", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("auto follows the operating system, in both directions", async ({ page }) => {
    /* Auto is a real third state, and the mechanism is worth pinning because it
       is not the obvious one: next-themes stores "system" as the PREFERENCE and
       writes the RESOLVED register to data-theme, so the attribute is always
       "light" or "dark". What makes Auto real is that it tracks the OS — which
       is what this emulates and asserts, rather than checking for a literal
       "system" attribute that will never appear. */
    await page.emulateMedia({ colorScheme: "light" });
    await page.goto("/");
    await page.getByRole("button", { name: "Night", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");

    await page.getByRole("button", { name: "Auto", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");

    await page.emulateMedia({ colorScheme: "dark" });
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("the auto preference itself is what persists", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Auto", exact: true }).click();
    const stored = await page.evaluate(() => localStorage.getItem("theme"));
    expect(stored).toBe("system");
  });

  test("both registers actually repaint the page", async ({ page }) => {
    await page.goto("/");
    const bg = async () =>
      page.evaluate(() => getComputedStyle(document.body).backgroundColor);
    await page.getByRole("button", { name: "Night", exact: true }).click();
    const dark = await bg();
    await page.getByRole("button", { name: "Day", exact: true }).click();
    const light = await bg();
    expect(dark).not.toBe(light);
  });
});

test.describe("language", () => {
  test("Arabic flips the document direction, not only the strings", async ({ page }) => {
    await page.goto("/brand");
    await page.getByRole("button", { name: "العربية", exact: true }).click();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    await expect(page.locator("html")).toHaveAttribute("lang", "ar");
  });

  test("the nav mirrors under RTL", async ({ page }) => {
    await page.goto("/");
    const first = page.getByRole("navigation", { name: /sections|الأقسام/i }).getByRole("link").first();
    const ltrBox = await first.boundingBox();
    await page.getByRole("button", { name: "العربية", exact: true }).click();
    await page.waitForTimeout(300);
    const rtlBox = await first.boundingBox();
    expect(rtlBox!.x, "the first tab should move to the right half").toBeGreaterThan(ltrBox!.x);
  });

  test("numerals and codes stay left-to-right inside an Arabic document", async ({ page }) => {
    /* The bug this catches: bidi reorders an LTR run it is not told to isolate,
       so a trading day 07:00 – 23:30 renders as 23:30 – 07:00. It throws no
       error and looks fine to a reader who does not read Arabic. */
    await page.goto("/brand");
    await page.getByRole("button", { name: "العربية", exact: true }).click();
    await page.waitForTimeout(300);
    const hours = await page.locator(".faint.num").first().innerText();
    expect(hours).toMatch(/^0?\d:\d\d\s*–\s*\d\d:\d\d$/);
    const [open, close] = hours.split("–").map((s) => s.trim());
    expect(open < close || close < "06:00", `hours read backwards: ${hours}`).toBeTruthy();
  });

  test("the language choice persists", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "हिन्दी", exact: true }).click();
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  });
});

test.describe("responsive", () => {
  test("no horizontal scroll at 360px on any tab", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 780 });
    for (const route of ROUTES) {
      await page.goto(route);
      const { doc, win } = await page.evaluate(() => ({
        doc: document.documentElement.scrollWidth,
        win: window.innerWidth,
      }));
      expect(doc, `${route} overflows at 360px`).toBeLessThanOrEqual(win + 1);
    }
  });

  test("a wide table scrolls inside its own box rather than the page", async ({ page }) => {
    await page.setViewportSize({ width: 360, height: 780 });
    await page.goto("/data");
    const box = page.locator(".scroll-x").first();
    await expect(box).toHaveCSS("overflow-x", "auto");
  });
});

test.describe("accessibility", () => {
  async function scan(page: Page, route: string) {
    await page.goto(route);
    const results = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(
      serious,
      `${route}: ${serious.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
    ).toEqual([]);
  }

  for (const route of ["/", "/data", "/brand", "/forecast"]) {
    test(`${route} has no serious axe violations`, async ({ page }) => {
      await scan(page, route);
    });
  }

  test("the dark register is scanned too", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Night", exact: true }).click();
    const results = await new AxeBuilder({ page }).withTags(["wcag2aa"]).analyze();
    const serious = results.violations.filter(
      (v) => v.impact === "serious" || v.impact === "critical",
    );
    expect(serious.map((v) => v.id)).toEqual([]);
  });

  test("the skip link is the first focusable element", async ({ page }) => {
    await page.goto("/");
    await page.keyboard.press("Tab");
    await expect(page.locator(":focus")).toHaveText(/skip to content/i);
  });
});

test.describe("data provenance reaches the screen", () => {
  test("every dataset shows a label and a licence", async ({ page }) => {
    await page.goto("/data");
    const cards = page.locator("article.card");
    const n = await cards.count();
    expect(n).toBeGreaterThanOrEqual(5);
    for (let i = 0; i < n; i++) {
      await expect(cards.nth(i).locator(".chip-label")).toBeVisible();
      await expect(cards.nth(i).getByText(/Licence/i)).toBeVisible();
    }
  });

  test("the generated series is labelled simulated on the page", async ({ page }) => {
    await page.goto("/data");
    await expect(page.getByText("simulated", { exact: true }).first()).toBeVisible();
  });
});
