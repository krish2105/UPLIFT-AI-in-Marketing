/* Capture every design direction in both registers, at phone and desktop width.
 *
 * These are the images the owner chooses from, and they are regenerated rather
 * than hand-collected so the choice is made against the current code.
 */
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "..", "..", "..", "docs", "images", "directions");
const BASE = process.env.BASE_URL ?? "http://localhost:3001";
const DIRECTIONS = ["almanac", "souk", "daypart"];
const REGISTERS = ["dark", "light"];

mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch();
for (const width of [1440, 390]) {
  const page = await browser.newPage({ viewport: { width, height: 1000 }, deviceScaleFactor: 2 });
  for (const direction of DIRECTIONS) {
    for (const register of REGISTERS) {
      await page.goto(`${BASE}/design?d=${direction}&r=${register}&w=full`, { waitUntil: "networkidle" });
      // Drive the real controls rather than injecting state, so the screenshot
      // shows what a visitor clicking those buttons actually gets.
      await page.getByRole("button", { name: labelFor(direction), exact: true }).click();
      await page.getByRole("button", { name: register === "dark" ? "Night" : "Day", exact: true }).click();
      // The control bar is sticky, which is right for using the page and wrong
      // for capturing it — it overlays the top of the specimen.
      await page.addStyleTag({ content: "header{position:static !important}" });
      await page.waitForTimeout(450);
      const target = page.locator(`[data-direction="${direction}"]`);
      const file = join(OUT, `${direction}-${register}-${width}.png`);
      await target.screenshot({ path: file });
      console.log(`  ${direction}/${register}/${width}px -> ${file.split("/docs/")[1]}`);
    }
  }
  await page.close();
}
await browser.close();

function labelFor(d) {
  return { almanac: "Almanac", souk: "Night Souk", daypart: "Daypart" }[d];
}
