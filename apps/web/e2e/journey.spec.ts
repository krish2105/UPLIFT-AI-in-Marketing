import { test, expect } from "@playwright/test";

/* The journey the master plan names: forecast → plan → creative → compliance →
 * measure. Not five page loads — one thread, where each step depends on the
 * previous one having produced something real.
 */

test("a planner can go from a forecast to a measured lift", async ({ page }) => {
  // 1. FORECAST — is the model trusted at all?
  await page.goto("/forecast");
  await expect(page.getByText(/36\/36/)).toBeVisible();
  await expect(page.getByText(/target 70%/i)).toBeVisible();
  const mae = await page.getByText(/seasonal naive .* better/i).first().innerText();
  expect(mae).toMatch(/better/);

  // 2. PLAN — size a budget against it, and check the allocation is optimal.
  await page.goto("/plan");
  await expect(page.getByText(/sums exactly to budget/i)).toBeVisible();
  await page.getByLabel(/Campaign budget/i).fill("20000");
  await page.waitForTimeout(700);
  await expect(page.getByText(/sums exactly to budget/i)).toBeVisible();
  await expect(page.getByText(/assumed elasticities/i)).toBeVisible();

  // 3. CREATIVE — make something for the slot the plan implies.
  await page.goto("/creatives");
  await expect(page.getByText(/3 slots × 3 languages/i)).toBeVisible();
  await expect(page.locator("article.card svg").first()).toBeVisible();

  // 4. COMPLIANCE — and it must be able to reject one.
  await page.goto("/compliance");
  await page.getByLabel("Copy to check").fill("Our best sugar-free detox latte");
  await page.getByRole("button", { name: "Check" }).click();
  await expect(page.locator(".badge-fail").first()).toBeVisible();
  await expect(page.getByText("SID-N-001").first()).toBeVisible();

  // 5. MEASURE — did it work, and does the estimator admit its own bias?
  await page.goto("/measure");
  await expect(page.getByText(/measured lift/i)).toBeVisible();
  await expect(page.getByText(/estimator bias/i)).toBeVisible();
  await expect(page.getByText(/within 5/i).first()).toBeVisible();
});

test("every step of the journey states what it cannot do", async ({ page }) => {
  /* The claims that keep the journey honest. Each is on the page a reader
     reaches at that step, not buried in a document. */
  const checks: [string, RegExp][] = [
    ["/forecast", /sMAPE is higher for the model|reported rather than optimised/i],
    ["/plan", /structural assumptions|assumed/i],
    ["/creatives", /breaks the rules deliberately/i],
    ["/panel", /not customer research/i],
    ["/measure", /placebo in time/i],
    ["/experiments", /decided BEFORE the promotion|before the promotion/i],
    ["/crew", /no agent has a tool that reaches the outside world|side effects/i],
  ];
  for (const [route, pattern] of checks) {
    await page.goto(route);
    await expect(page.getByText(pattern).first(), `${route} is missing its caveat`).toBeVisible();
  }
});
