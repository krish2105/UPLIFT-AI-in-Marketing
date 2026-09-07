import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

/* The frame-rate measurement, run alone.
 *
 * It is the one test whose RESULT depends on what else is running: inside the
 * parallel suite it measured 30 fps, and by itself 60 — same scene, same
 * machine, different contention. So it is excluded from `make e2e` by
 * testIgnore there and given this config instead, which reuses that file's
 * servers and overrides only the scheduling.
 *
 * A performance number measured next to 78 other tests describes the runner.
 */
export default defineConfig({
  ...base,
  testIgnore: undefined,
  testMatch: "**/frames.spec.ts",
  fullyParallel: false,
  workers: 1,
});
