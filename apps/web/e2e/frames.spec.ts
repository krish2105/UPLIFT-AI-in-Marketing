import { test, expect } from "@playwright/test";
import { writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";

/* The 60 fps target, measured.
 *
 * Every other target in this project carries a number from docs/results/. This
 * one carried a sentence — "≈224 instanced boxes; 60 fps is not in doubt" —
 * written before the scene existed. An untested performance claim is the one
 * kind of claim that is always true right up until someone opens it on a
 * laptop.
 *
 * WHAT THIS MEASURES, AND WHAT IT DOES NOT
 * Frame intervals are sampled with requestAnimationFrame in headless Chromium
 * while the day scrubber is dragged — the interaction that actually moves
 * geometry. Headless has no display to sync to, so it is NOT a claim about a
 * particular laptop; it is a claim that the scene's per-frame work leaves room
 * inside a 16.7 ms budget on this machine. The floor is set below 60 on
 * purpose, because a CI box under load that fails at 58 fps teaches nothing and
 * gets deleted. The median is recorded either way.
 */

const RESULTS = join(__dirname, "..", "..", "..", "docs", "results");
const BUDGET_MS = 1000 / 60;
const FLOOR_FPS = 30;

// Excluded from the default suite by testIgnore and run alone via `make frames`.
// Sharing four cores with 78 other tests halved the median, which measures the
// runner rather than the scene.
test("the terrain holds its frame budget while the horizon is scrubbed", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Terrain", exact: true }).click();
  const canvas = page.locator("canvas").first();
  await expect(canvas).toBeVisible();
  await page.waitForTimeout(1200); // let the scene settle and textures upload

  // Start sampling, then drive the scrubber so the measurement covers work,
  // not an idle scene sitting on its last frame.
  await page.evaluate(() => {
    const w = window as unknown as { __frames: number[] };
    w.__frames = [];
    let last = performance.now();
    const tick = (t: number) => {
      w.__frames.push(t - last);
      last = t;
      if (w.__frames.length < 400) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });

  const slider = page.getByLabel("Day in the horizon");
  await slider.focus();
  for (let i = 0; i < 40; i++) await slider.press("ArrowRight");

  await page.waitForTimeout(1500);
  const frames: number[] = await page.evaluate(
    () => (window as unknown as { __frames: number[] }).__frames,
  );

  // The first sample is the gap since sampling began, not a rendered frame.
  const d = frames.slice(1).sort((a, b) => a - b);
  expect(d.length).toBeGreaterThan(60);

  const at = (q: number) => d[Math.min(d.length - 1, Math.floor(d.length * q))];
  const median = at(0.5);
  const p95 = at(0.95);
  /* Not "over 16.67 ms": at 60 Hz the nominal interval lands a hair above the
     budget, so that counts two thirds of a perfectly smooth run as a miss. A
     frame a viewer actually notices is one that ate a second vsync. */
  const dropped = d.filter((x) => x > BUDGET_MS * 1.5).length / d.length;

  const report = {
    task: "D1-frames",
    generated_by: "apps/web/e2e/frames.spec.ts",
    scene: "terrain, 4 lanes x 56 days, event bands and weather ribbon",
    interaction: "40 keyboard steps of the day scrubber",
    samples: d.length,
    budget_ms: +BUDGET_MS.toFixed(2),
    median_frame_ms: +median.toFixed(2),
    p95_frame_ms: +p95.toFixed(2),
    median_fps: +(1000 / median).toFixed(1),
    p95_fps: +(1000 / p95).toFixed(1),
    dropped_frame_share: +dropped.toFixed(3),
    dropped_frame_threshold_ms: +(BUDGET_MS * 1.5).toFixed(2),
    floor_fps: FLOOR_FPS,
    measured_alone: true,
    meets_floor: 1000 / median >= FLOOR_FPS,
    note: [
      "Headless Chromium has no display to synchronise with, so this is not a",
      "claim about any particular laptop. It measures whether the scene's",
      "per-frame work fits inside a 60 fps budget on this machine, and it is",
      "recorded rather than asserted because the plan's original wording — '60",
      "fps is not in doubt' — was written before the scene existed.",
    ].join(" "),
  };

  mkdirSync(RESULTS, { recursive: true });
  writeFileSync(join(RESULTS, "D1-frames.json"), JSON.stringify(report, null, 2) + "\n");
  console.log(
    `frames: median ${report.median_fps} fps, p95 ${report.p95_fps} fps, ` +
      `${(dropped * 100).toFixed(1)}% dropped`,
  );

  expect(report.median_fps).toBeGreaterThanOrEqual(FLOOR_FPS);
});
