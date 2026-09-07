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
  /* The frame-rate measurement is excluded from the default run and has its own
     command, because it is the one test whose RESULT depends on what else is
     running. Inside the parallel suite it measured 30 fps; alone, 60 — same
     scene, same machine, different contention. A number that moves with the
     neighbours is not a measurement of the thing it names. */
  testIgnore: "**/frames.spec.ts",
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
      /* Never reused, even locally. A uvicorn process left over from an earlier
         run holds the port and answers every request from the code it was
         started with, so the suite goes green against an API that no longer
         exists in the working tree — which is how a Security page test passed
         while the section it asserts was missing. Refusing to reuse turns that
         into a loud "port in use" instead of a quiet false pass. The web server
         below is safe to reuse: the dev server recompiles from these files. */
      reuseExistingServer: false,
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
