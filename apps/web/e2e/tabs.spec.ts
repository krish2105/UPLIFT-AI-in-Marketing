import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

/* Every tab now renders measured output rather than a scaffold, so each one has
 * something specific that must be on it. These are the assertions that would
 * catch a page quietly degrading to an empty state — which, because the empty
 * state is deliberately calm and well-written, is easy to miss by eye.
 */

test.describe("no tab is a scaffold any more", () => {
  const MUST_CONTAIN: [string, RegExp][] = [
    ["/forecast", /weeks beaten/i],
    ["/plan", /marginal spread/i],
    ["/segments", /bootstrap stability/i],
    ["/creatives", /compliant/i],
    ["/compliance", /recall on the gold set/i],
    ["/panel", /not customer research/i],
    ["/measure", /measured lift/i],
    ["/experiments", /minimum detectable|MDE/i],
    ["/crew", /side effects/i],
    ["/security", /enforced in code/i],
    ["/ask", /corpus/i],
    ["/report", /figures typed by hand|not generated/i],
  ];

  for (const [route, pattern] of MUST_CONTAIN) {
    test(`${route} shows its own measured content`, async ({ page }) => {
      await page.goto(route);
      await expect(page.getByText(/API unreachable/i)).toHaveCount(0);
      await expect(page.getByText(pattern).first()).toBeVisible();
    });
  }
});

test.describe("the numbers on screen are the measured ones", () => {
  test("the forecast tab shows the win rate from the results file", async ({ page }) => {
    await page.goto("/forecast");
    // 36 of 36 site-weeks, against a 70% target.
    await expect(page.getByText(/36\/36/)).toBeVisible();
    await expect(page.getByText(/target 70%/i)).toBeVisible();
  });

  test("the allocator sums to its budget and reports the KKT spread", async ({ page }) => {
    await page.goto("/plan");
    await expect(page.getByText(/sums exactly to budget/i)).toBeVisible();
    await expect(page.getByText(/0 = equal marginal return/i)).toBeVisible();
  });

  test("the uplift tab reports the estimator's own bias, not just the lift", async ({ page }) => {
    await page.goto("/measure");
    await expect(page.getByText(/placebo in time/i)).toBeVisible();
    await expect(page.getByText(/estimator bias/i)).toBeVisible();
  });

  test("compliance reports precision beside recall", async ({ page }) => {
    await page.goto("/compliance");
    await expect(page.getByText(/precision/i).first()).toBeVisible();
    await expect(page.getByText(/a rule that flags everything/i)).toBeVisible();
  });
});

test.describe("the safety claim is on screen", () => {
  test("every crew row declares no side effects", async ({ page }) => {
    await page.goto("/crew");
    const badges = page.locator("tbody .badge-pass");
    const n = await badges.count();
    expect(n).toBeGreaterThanOrEqual(7);
    for (let i = 0; i < n; i++) await expect(badges.nth(i)).toHaveText("none");
  });

  test("the security scorecard names what verifies each control", async ({ page }) => {
    await page.goto("/security");
    await expect(page.getByText(/tests\/invariants\/test_no_side_effects\.py/).first()).toBeVisible();
  });

  test("the page shows the attacks, not only the assurances", async ({ page }) => {
    /* A scorecard alone is a list of things someone believes. The harness result
       beside it is what happened when they were attacked, so the page has to
       carry the attempts themselves — including the one that succeeded. */
    await page.goto("/security");
    await expect(page.getByRole("heading", { name: /when the claims were attacked/i })).toBeVisible();

    const rows = page.locator("table.data tbody tr");
    await expect.poll(() => rows.count()).toBeGreaterThanOrEqual(30);

    // The classic injection is present and recorded as held.
    const injected = rows.filter({ hasText: "Ignore all previous instructions" }).first();
    await expect(injected.locator(".badge-pass")).toHaveText("held");

    // The string that used to work. `X-Mawsim-Role: ADMIN ` engaged the kill
    // switch and this row read "broke · accepted"; a role is a signed token now,
    // so it holds. The row is asserted by NAME rather than by count, because
    // "48 of 48 held" would still pass if this particular case quietly stopped
    // being run.
    const retired = rows.filter({ hasText: "the exact string that used to work" }).first();
    await expect(retired.locator(".badge-pass")).toHaveText("held");

    // And a token attack, so the table is shown to cover the mechanism that
    // replaced it rather than only the one it retired.
    const forged = rows.filter({ hasText: "rewrite a viewer token's role to admin" }).first();
    await expect(forged.locator(".badge-pass")).toHaveText("held");
  });
});

test.describe("compliance actually catches things", () => {
  test("a violating line is rejected with its rule and source", async ({ page }) => {
    await page.goto("/compliance");
    await page.getByLabel("Copy to check").fill("Our best sugar-free detox latte");
    await page.getByRole("button", { name: "Check" }).click();
    await expect(page.locator(".badge-fail").first()).toBeVisible();
    await expect(page.getByText("SID-N-001").first()).toBeVisible();
  });

  test("a discount with its terms stated is permitted", async ({ page }) => {
    /* The false-positive case. A tool that flags every discount gets switched
       off, and then it catches nothing at all. */
    await page.goto("/compliance");
    await page.getByLabel("Copy to check").fill("Was AED 32, now AED 24. Until 30 September.");
    await page.getByRole("button", { name: "Check" }).click();
    await expect(page.locator(".badge-pass").first()).toBeVisible();
  });
});

test.describe("ask cites or refuses", () => {
  test("a question in the corpus returns passages with sources", async ({ page }) => {
    await page.goto("/ask");
    await page.getByLabel("Question").fill("can we say sugar free");
    await page.getByRole("button", { name: "Ask" }).click();
    await expect(page.getByText("SID-N-001").first()).toBeVisible();
  });

  test("a question outside the corpus is refused rather than answered", async ({ page }) => {
    await page.goto("/ask");
    await page.getByLabel("Question").fill("zzzz qqqq xxxx");
    await page.getByRole("button", { name: "Ask" }).click();
    await expect(page.getByText(/No match|Nothing in the corpus matched/i).first()).toBeVisible();
  });
});

test.describe("accessibility across the new tabs", () => {
  for (const route of ["/creatives", "/compliance", "/panel", "/measure", "/experiments", "/crew", "/security", "/ask", "/report", "/plan", "/segments"]) {
    test(`${route} has no serious axe violations`, async ({ page }) => {
      await page.goto(route);
      /* color-contrast is disabled here, and measured properly elsewhere.
       *
       * axe reported the theme toggle's pressed label at 3.04:1, intermittently —
       * only when that button sits in one register. The computed styles are
       * L*96.7 on L*12.6, and this project's own gate measures the pair at
       * 14.86:1 (docs/results/A2-contrast.json). axe read the foreground
       * correctly and the background wrongly: it reported #858f92, which is the
       * BORDER token, because these tokens resolve to CSS Color 4 `lab()` values
       * its parser does not handle.
       *
       * Suppressing a failing accessibility rule is normally how a suite starts
       * lying, so to be explicit: contrast is not going unchecked. It is measured
       * in OKLCH by apps/web/scripts/check-contrast.mjs across 38 pairs in both
       * registers, which is stricter than axe and does not guess. Chasing this
       * added the pressed-toggle composite to that gate, where it had never been
       * measured at all. Every other axe rule still runs here.
       */
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .disableRules(["color-contrast"])
        .analyze();
      const serious = results.violations.filter(
        (v) => v.impact === "serious" || v.impact === "critical",
      );
      expect(
        serious,
        `${route}: ${serious.map((v) => `${v.id} (${v.nodes.length})`).join(", ")}`,
      ).toEqual([]);
    });
  }
});
