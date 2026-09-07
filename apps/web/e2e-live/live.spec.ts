import { test, expect } from "@playwright/test";

/* What must be true of the deployed instance, and nothing more.
 *
 * These assert deployment properties — the API answers, CORS lets the web app
 * reach it, the datasets are present, the disclaimer is on the page. Everything
 * about behaviour is covered by the local suite; repeating it here would make a
 * cold free instance look like a regression.
 */

const API = process.env.LIVE_API_URL;
const WEB = process.env.LIVE_WEB_URL;

test.skip(!API || !WEB, "set LIVE_API_URL and LIVE_WEB_URL to run the live smoke test");

test("the API answers and reports its datasets", async ({ request }) => {
  const res = await request.get(`${API}/healthz`, { timeout: 120_000 });
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.brand.fictional).toBe(true);
  // A deployed instance whose build did not run the pipelines comes up with an
  // empty database. That is the failure this exists to catch.
  expect(body.empty_datasets, `empty on the deployed instance: ${body.empty_datasets}`).toEqual([]);
});

test("every dataset reaches the deployed instance with its provenance", async ({ request }) => {
  const res = await request.get(`${API}/data/freshness`, { timeout: 120_000 });
  const body = await res.json();
  expect(body.datasets.length).toBeGreaterThanOrEqual(5);
  for (const d of body.datasets) {
    expect(d.licence, `${d.key} has no licence`).toBeTruthy();
    expect(d.label, `${d.key} has no label`).toBeTruthy();
    expect(d.rows, `${d.key} is empty`).toBeGreaterThan(0);
  }
});

test("the web app loads and carries the disclaimer", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(page.locator("footer.footer").getByText(/fictional brand/i)).toBeVisible();
});

test("the web app can actually reach the API across origins", async ({ page }) => {
  /* The single most common deployment failure: the app builds, the API runs,
     and CORS_ORIGINS does not match the Vercel URL. The page then renders its
     honest "API unreachable" state, which looks like a design decision rather
     than a misconfiguration. */
  await page.goto("/data");
  await expect(page.getByText(/API unreachable/i)).toHaveCount(0);
  await expect(page.locator("article.card").first()).toBeVisible();
});

test("the deployed shell still has all fifteen tabs", async ({ page }) => {
  await page.goto("/");
  const nav = page.getByRole("navigation", { name: /sections/i });
  await expect(nav.getByRole("link")).toHaveCount(15);
});

test("the deployed instance carries the red-team result, not just the scorecard", async ({
  page,
}) => {
  /* A deployment property, not a behavioural one: docs/results/E1-red-team.json
     is read from disk by the API, so it is exactly the kind of file a build can
     leave behind. If it is missing the section vanishes silently and the page
     falls back to a scorecard of assurances — which is what this project is
     trying not to ship. */
  await page.goto("/security");
  await expect(page.getByRole("heading", { name: /when the claims were attacked/i })).toBeVisible();
  /* Asserted by NAME, not by count: "48 of 48 held" would still pass if the
     token attacks quietly stopped being run. This row is the mechanism that
     replaced the forgeable header, so its presence is the thing worth checking
     reached production. */
  await expect(
    page
      .locator("table.data tbody tr")
      .filter({ hasText: "rewrite a viewer token's role to admin" })
      .first(),
  ).toContainText(/held/i);
});

test("the deployed instance has no Admin, and says so", async ({ request }) => {
  /* Fail-closed, checked in production rather than assumed from the code.
     No signing secret is set on the public instance, so the capability is
     ABSENT rather than open — and the endpoint that used to grant it with a
     header now refuses. A deployment that quietly acquired a secret, or one
     where the header still worked, both show up here. */
  const roles = await request.get(`${API}/admin/roles`, { timeout: 120_000 });
  expect(roles.status()).toBe(200);
  const body = await roles.json();
  expect(body.you_are).toBe("viewer");
  expect(body.admin_available_on_this_instance).toBe(false);

  const forged = await request.get(`${API}/admin/killswitch/engage?reason=live+probe`, {
    headers: { "X-Mawsim-Role": "ADMIN " },
    timeout: 120_000,
  });
  expect(forged.status()).toBe(403);
  expect((await request.get(`${API}/admin/killswitch`)).json()).resolves.toMatchObject({
    engaged: false,
  });
});
