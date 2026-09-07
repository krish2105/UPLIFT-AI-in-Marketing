import { defineConfig, devices } from "@playwright/test";

/* The e2e suite starts both servers itself.
 *
 * It is kept out of `make check` on purpose: `check` is the bar a contributor
 * runs constantly, and it should not depend on two processes and a built
 * database. `make e2e` is the deliberate, slower gate.
 *
 * Ports are non-default because the sibling Term 4 projects run on 3000 and
 * 8000, and a suite that silently tests another application's API is worse than
 * one that fails to start.
 */
const API_PORT = 8031;
const WEB_PORT = 3031;

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: [
    {
      command: `cd ../.. && uv run uvicorn services.api.main:app --port ${API_PORT}`,
      url: `http://localhost:${API_PORT}/healthz`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { CORS_ORIGINS: `http://localhost:${WEB_PORT}` },
    },
    {
      command: `npm run dev -- --port ${WEB_PORT}`,
      url: `http://localhost:${WEB_PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 180_000,
      env: { NEXT_PUBLIC_API_BASE: `http://localhost:${API_PORT}` },
    },
  ],
});
