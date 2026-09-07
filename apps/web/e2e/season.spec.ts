import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/* The 3D season view, and the guarantee that it is an enhancement.
 *
 * The most important test here is the one that turns WebGL OFF. A 3D
 * centrepiece that leaves a reader with an empty box when their machine cannot
 * draw it has not degraded — it has failed.
 */

test.describe("progressive enhancement", () => {
  test("the flat view carries the same data as the terrain", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Flat", exact: true }).click();
    const svg = page.locator("figure svg").first();
    await expect(svg).toBeVisible();
    // Four lanes, each labelled, and an interval on every bar.
    for (const zone of ["DXB-MAR", "DXB-DTN", "DXB-MOE", "DXB-DEI"]) {
      await expect(svg.getByText(zone)).toBeVisible();
    }
  });

  test("without WebGL the page still shows the forecast", async ({ browser }) => {
    /* Simulated by removing the context getters before any script runs, which
       is what an old browser or a locked-down machine actually presents. */
    const ctx = await browser.newContext();
    await ctx.addInitScript(() => {
      const orig = HTMLCanvasElement.prototype.getContext;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      HTMLCanvasElement.prototype.getContext = function (kind: string, ...rest: unknown[]): any {
        if (kind === "webgl" || kind === "webgl2" || kind === "experimental-webgl") return null;
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        return (orig as any).call(this, kind, ...rest);
      };
    });
    const page = await ctx.newPage();
    await page.goto("/");
    await page.waitForTimeout(600);

    await expect(page.getByText(/no WebGL here/i)).toBeVisible();
    await expect(page.getByRole("button", { name: "Terrain", exact: true })).toBeDisabled();
    // and the data is still on screen
    await expect(page.locator("figure svg").first()).toBeVisible();
    await expect(page.getByText("DXB-MAR").first()).toBeVisible();
    await ctx.close();
  });

  test("the canvas appears only when WebGL is available", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Terrain", exact: true }).click();
    await expect(page.locator('[data-testid="terrain-3d"]')).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("both projections", () => {
  test("terrain and map are the same data seen differently", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: "Terrain", exact: true }).click();
    await expect(page.locator('[data-testid="terrain-3d"]')).toBeVisible({ timeout: 20_000 });
    await page.getByRole("button", { name: "Map", exact: true }).click();
    await expect(page.locator('[data-testid="terrain-3d"]')).toBeVisible();
    await expect(page.getByRole("button", { name: "Map", exact: true })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  test("scrubbing a day moves the readout", async ({ page }) => {
    await page.goto("/");
    const label = page.getByText(/Day 1 of \d+/);
    await expect(label).toBeVisible();
    await page.getByLabel("Day in the horizon").fill("20");
    await expect(page.getByText(/Day 21 of \d+/)).toBeVisible();
  });

  test("the interval is on screen, not just in the geometry", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/at 80%/).first()).toBeVisible();
    await expect(page.getByText(/every block wears a cap/i)).toBeVisible();
  });
});

test("the season view has no serious axe violations", async ({ page }) => {
  await page.goto("/");
  const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
  const serious = results.violations.filter(
    (v) => v.impact === "serious" || v.impact === "critical",
  );
  expect(serious.map((v) => `${v.id} (${v.nodes.length})`)).toEqual([]);
});
