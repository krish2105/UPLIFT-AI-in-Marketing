import { defineConfig, devices } from "@playwright/test";

/* The live smoke test.
 *
 * Runs against the deployed pair rather than a local one, so it catches the
 * failures only deployment produces: a CORS origin that does not match, an
 * empty database on an ephemeral filesystem, a build that shipped without the
 * pipelines having run.
 *
 * The first request wakes a sleeping free instance and takes about a minute, so
 * the timeouts here are deliberately generous — a timeout that fails on a cold
 * start would report "the deployment is broken" every time nobody had visited.
 */
export default defineConfig({
  testDir: "./e2e-live",
  timeout: 120_000,
  expect: { timeout: 90_000 },
  retries: 1,
  reporter: "list",
  use: {
    baseURL: process.env.LIVE_WEB_URL,
    trace: "on-first-retry",
    navigationTimeout: 90_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
