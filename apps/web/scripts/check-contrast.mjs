/* The contrast gate.
 *
 * WHY THIS EXISTS AS A BUILD STEP
 * -------------------------------
 * Every accessibility claim a project makes is either measured or it is a hope.
 * This parses the OKLCH values out of the token files, converts them properly
 * (OKLCH -> OKLab -> linear sRGB -> sRGB, with gamut clipping made visible),
 * computes WCAG 2.1 contrast, and FAILS the build when a pair falls short.
 *
 * It runs over EVERY design direction and BOTH registers, so a direction that
 * only works in the dark cannot quietly ship. The `@register` and `@direction`
 * comment markers in the token files are load-bearing: this file parses them.
 *
 * Floors: body text 4.5:1, large/display text 3:1, UI borders and non-text
 * indicators 3:1 (WCAG 1.4.11). Where a token is out of sRGB gamut the report
 * says so rather than silently clipping to something that measures differently
 * from what a browser will draw.
 */

import { readFileSync, writeFileSync, readdirSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const STYLES = join(HERE, "..", "styles");
const RESULTS = join(HERE, "..", "..", "..", "docs", "results");

/* ── colour maths ───────────────────────────────────────────────────────── */

/** OKLCH -> linear sRGB. Björn Ottosson's matrices, unmodified. */
function oklchToLinearSrgb(L, C, hDeg) {
  const h = (hDeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);

  const l_ = L + 0.3963377774 * a + 0.2158037573 * b;
  const m_ = L - 0.1055613458 * a - 0.0638541728 * b;
  const s_ = L - 0.0894841775 * a - 1.291485548 * b;

  const l = l_ ** 3;
  const m = m_ ** 3;
  const s = s_ ** 3;

  return [
    +4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}

const clamp01 = (x) => Math.min(1, Math.max(0, x));

/** WCAG relative luminance works on LINEAR light, so no gamma round-trip here. */
function relativeLuminance(L, C, h) {
  const [r, g, b] = oklchToLinearSrgb(L, C, h);
  const outOfGamut = [r, g, b].some((v) => v < -0.0005 || v > 1.0005);
  const lum = 0.2126 * clamp01(r) + 0.7152 * clamp01(g) + 0.0722 * clamp01(b);
  return { lum, outOfGamut };
}

function contrast(a, b) {
  const hi = Math.max(a, b) + 0.05;
  const lo = Math.min(a, b) + 0.05;
  return hi / lo;
}

/* ── token parsing ──────────────────────────────────────────────────────── */

const OKLCH = /oklch\(\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*(?:\/\s*[\d.]+\s*)?\)/;

/** Split a token file into register blocks marked by `@register <name>`. */
function parseDirection(css) {
  // Before the direction was chosen this parsed an `@direction` marker per
  // file. One direction now ships, so the file name is the identity.
  const direction = css.match(/@direction\s+([a-z-]+)/)?.[1] ?? "mawsim";

  const registers = {};
  // A register runs from its marker to the next marker or end of file.
  const marks = [...css.matchAll(/@register\s+([a-z]+)/g)];
  if (marks.length === 0) throw new Error(`${direction}: no @register markers`);

  marks.forEach((mark, i) => {
    const start = mark.index;
    const end = i + 1 < marks.length ? marks[i + 1].index : css.length;
    const block = css.slice(start, end);
    const tokens = registers[mark[1]] ?? (registers[mark[1]] = {});
    for (const line of block.split("\n")) {
      const decl = line.match(/^\s*(--[a-z0-9-]+)\s*:\s*(.+?);/);
      if (!decl) continue;
      const c = decl[2].match(OKLCH);
      // Later declarations win, exactly as the cascade would resolve them.
      if (c) tokens[decl[1]] = [+c[1], +c[2], +c[3]];
    }
  });
  return { direction, registers };
}

/* ── what must be legible against what ──────────────────────────────────── */

/** [foreground, background, floor, why]. Every direction is held to all of it. */
const PAIRS = [
  ["--text", "--bg", 4.5, "body text on the page ground"],
  ["--text", "--surface", 4.5, "body text on a card"],
  ["--text", "--surface-raised", 4.5, "body text on a raised card"],
  ["--text-muted", "--bg", 4.5, "secondary text on the ground"],
  ["--text-muted", "--surface", 4.5, "secondary text on a card"],
  ["--text-faint", "--bg", 3.0, "captions and axis labels, large or incidental"],
  ["--border-strong", "--bg", 3.0, "focus rings and input borders (WCAG 1.4.11)"],
  ["--border", "--surface", 1.5, "hairline separation, decorative floor only"],
  ["--accent-text", "--bg", 4.5, "the signal colour used as text"],
  ["--accent-text", "--surface", 4.5, "the signal colour as text on a card"],
  ["--text-on-accent", "--accent", 4.5, "text sitting on a filled signal chip"],
  ["--sig-forecast-text", "--bg", 4.5, "forecast series label"],
  ["--sig-actual-text", "--bg", 4.5, "measured series label"],
  ["--pass-text", "--bg", 4.5, "compliance PASS wording"],
  ["--fail-text", "--bg", 4.5, "compliance FAIL wording"],
  ["--sig-forecast", "--bg", 3.0, "forecast line against the plot ground"],
  ["--sig-actual", "--bg", 3.0, "measured line against the plot ground"],
];

/* ── run ────────────────────────────────────────────────────────────────── */

const files = readdirSync(STYLES).filter((f) => /^tokens(\..+)?\.css$/.test(f));
if (files.length === 0) {
  console.error("contrast gate FAILED: no tokens.css found in styles/");
  process.exit(1);
}

const report = { generated_by: "apps/web/scripts/check-contrast.mjs", directions: {} };
const failures = [];
let measured = 0;

for (const file of files.sort()) {
  const { direction, registers } = parseDirection(readFileSync(join(STYLES, file), "utf8"));
  report.directions[direction] = { file: `apps/web/styles/${file}`, registers: {} };

  for (const [register, tokens] of Object.entries(registers)) {
    const rows = [];
    for (const [fgName, bgName, floor, why] of PAIRS) {
      const fg = tokens[fgName];
      const bg = tokens[bgName];
      if (!fg || !bg) {
        failures.push(`${direction}/${register}: missing ${!fg ? fgName : bgName}`);
        continue;
      }
      const f = relativeLuminance(...fg);
      const b = relativeLuminance(...bg);
      const ratio = contrast(f.lum, b.lum);
      const pass = ratio >= floor;
      measured++;
      rows.push({
        foreground: fgName,
        background: bgName,
        ratio: Math.round(ratio * 100) / 100,
        floor,
        pass,
        out_of_gamut: f.outOfGamut || b.outOfGamut,
        why,
      });
      if (!pass) {
        failures.push(
          `${direction}/${register}: ${fgName} on ${bgName} = ${ratio.toFixed(2)}:1, needs ${floor}:1 — ${why}`,
        );
      }
      if (f.outOfGamut || b.outOfGamut) {
        failures.push(
          `${direction}/${register}: ${fgName} on ${bgName} uses a colour outside sRGB; the browser will draw something other than what this measured`,
        );
      }
    }
    report.directions[direction].registers[register] = rows;
  }
}

report.pairs_measured = measured;
report.failures = failures;
report.pass = failures.length === 0;

mkdirSync(RESULTS, { recursive: true });
writeFileSync(join(RESULTS, "A2-contrast.json"), JSON.stringify(report, null, 2) + "\n");

if (failures.length) {
  console.error(`contrast gate FAILED — ${failures.length} of ${measured} measured pairs:\n`);
  for (const f of failures) console.error(`  ${f}`);
  console.error("\nRaise the token until it measures. Do not lower the floor.");
  process.exit(1);
}

console.log(
  `contrast gate passed — ${measured} pairs measured across ` +
    `${Object.keys(report.directions).length} direction(s), both registers. ` +
    `docs/results/A2-contrast.json written.`,
);
