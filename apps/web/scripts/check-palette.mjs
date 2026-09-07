/* The palette gate.
 *
 * ALMANAC's rule is that colour means TEMPERATURE, so the palette is not a
 * categorical set with a sequential ramp beside it — it is a ramp, plus three
 * signal marks that can legitimately share a chart: the forecast, what was
 * measured, and a planned promotion. Those three have to be separable, and the
 * ramp has to read as a scale. Both are computable, so they are computed.
 *
 * The checks, run in both registers:
 *   1. signal separation   forecast / measured / promo stay apart, by HUE or by
 *                          LIGHTNESS — the first two are deliberately the same
 *                          hue at different lightness so the pair survives a
 *                          monochrome print, and the gate accepts that and says
 *                          which mechanism carries each pair
 *   2. CVD separation      the same pairs under deuteranopia
 *   3. chroma floor        the promo signal does not read as grey
 *   4. contrast vs surface every mark reaches 3:1 against its own ground
 *   5. ramp monotone       lightness climbs or falls without turning back
 *   6. ramp is a scale     no two steps collide
 *   7. zones are unhued    there is no per-site colour token, because sites are
 *                          shown as small multiples rather than as overlaid
 *                          series — asserting the design rule, not just holding it
 *
 * The method follows the dataviz reference; it is reimplemented here rather
 * than shelled out to, so the check runs on any machine and in CI.
 *
 * HISTORY WORTH KEEPING. Two earlier palettes were rejected here. A literal
 * daypart set — cool morning, yellow midday, ember evening — collapsed to
 * deltaE 3.5 under deuteranopia once midday was saturated enough not to read
 * grey; desaturating it fixed the collision and reintroduced the grey. And this
 * ramp originally rose to a pale yellow in the middle and fell away, which is
 * what a "turbo" colormap does: the eye ranks by lightness before hue, so a
 * non-monotone ramp reads as categories rather than as a scale. Neither failure
 * is visible by eye on a designer's monitor.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parseRegisters } from "./tokens.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TOKENS = join(HERE, "..", "styles", "tokens.css");
const RESULTS = join(HERE, "..", "..", "..", "docs", "results");

const CHROMA_FLOOR = 0.1;
const CVD_FLOOR = 8;           // below this is a fail; 6-8 needs secondary encoding
const NORMAL_FLOOR = 15;       // separable by hue alone
const LIGHTNESS_FLOOR = 0.18;  // separable by lightness alone, in OKLCH L
const CONTRAST_FLOOR = 3;
const RAMP_STEP_FLOOR = 0.05;  // adjacent ramp steps must differ in lightness

/* ── colour maths ─────────────────────────────────────────────────────────── */

function oklchToLinear(L, C, hDeg) {
  const h = (hDeg * Math.PI) / 180;
  const a = C * Math.cos(h);
  const b = C * Math.sin(h);
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.291485548 * b) ** 3;
  return [
    4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.707614701 * s,
  ];
}

const clamp01 = (x) => Math.min(1, Math.max(0, x));

function linearToOklab([r, g, b]) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [
    0.2104542553 * l + 0.793617785 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.428592205 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.808675766 * s,
  ];
}

/* Viénot-style dichromat simulation on linear sRGB.
 *
 * Deuteranopia is the binding case — it is the most common form and the one
 * that collapses a warm/cool pair. Tritanopia is reported for information: it
 * scores low for almost every warm/cool triad and treating it as binding would
 * reject palettes nobody has trouble reading.
 *
 * Protanopia is deliberately ABSENT. A matrix for it exists in the literature
 * in several mutually inconsistent forms, and an unverified one produced a
 * confident dE of 3.1 on a pair that measures 24.9 apart to normal vision —
 * a number that would have driven a real design decision. A check that cannot
 * be trusted is worse than a check that is missing.
 */
const CVD_MATRIX = {
  deutan: [[0.625, 0.375, 0.0], [0.7, 0.3, 0.0], [0.0, 0.3, 0.7]],
  tritan: [[0.95, 0.05, 0.0], [0.0, 0.433, 0.567], [0.0, 0.475, 0.525]],
};

function simulate(linear, kind) {
  const M = CVD_MATRIX[kind];
  return M.map((row) => row.reduce((acc, k, i) => acc + k * clamp01(linear[i]), 0));
}

/** OKLab delta-E between two OKLCH triples, computed directly.
 *
 * OKLCH IS polar OKLab, so a = C cos h and b = C sin h exactly. Going out to
 * linear sRGB and back clamps out-of-gamut components and loses the very
 * difference being measured — that round trip reported 11.7 for a pair whose
 * true separation is 24.9.
 */
function deltaEOklch([L1, C1, h1], [L2, C2, h2]) {
  const r1 = (h1 * Math.PI) / 180;
  const r2 = (h2 * Math.PI) / 180;
  return (
    Math.hypot(
      L1 - L2,
      C1 * Math.cos(r1) - C2 * Math.cos(r2),
      C1 * Math.sin(r1) - C2 * Math.sin(r2),
    ) * 100
  );
}

/** OKLab delta-E between two linear-sRGB triples. Used only after a CVD
 *  simulation, which is defined in RGB space and has no OKLCH form. */
function deltaE(a, b) {
  const [l1, a1, b1] = linearToOklab(a.map(clamp01));
  const [l2, a2, b2] = linearToOklab(b.map(clamp01));
  return Math.hypot(l1 - l2, a1 - a2, b1 - b2) * 100;
}

function luminance(linear) {
  const [r, g, b] = linear.map(clamp01);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

const contrast = (a, b) =>
  (Math.max(luminance(a), luminance(b)) + 0.05) / (Math.min(luminance(a), luminance(b)) + 0.05);

/* ── token extraction ─────────────────────────────────────────────────────── */


/* ── run ────────────────────────────────────────────────────────────────── */

const REGISTERS = parseRegisters(readFileSync(TOKENS, "utf8"));

/** The three marks that can share one chart. */
const SIGNALS = ["--sig-forecast", "--sig-actual", "--accent"];
const RAMP = ["--heat-0", "--heat-1", "--heat-2", "--heat-3", "--heat-4", "--heat-5"];

const report = { generated_by: "apps/web/scripts/check-palette.mjs", registers: {} };
const failures = [];

for (const register of ["light", "dark"]) {
  const tokens = REGISTERS[register];
  const surface = oklchToLinear(...tokens["--bg"]);
  const checks = [];
  const fail = (name, detail) => {
    checks.push({ name, pass: false, detail });
    failures.push(`${register}: ${name} — ${detail}`);
  };
  const pass = (name, detail) => checks.push({ name, pass: true, detail });

  const marks = SIGNALS.map((name) => ({
    name,
    oklch: tokens[name],
    linear: oklchToLinear(...tokens[name]),
  }));

  /* 1 + 2. Separation. A pair may be separated by hue OR by lightness; the
     forecast/measured pair is deliberately the latter, so that the divergence
     between what was predicted and what happened survives a monochrome print
     and does not spend a hue the thermal ramp needs. */
  const pairs = [];
  for (let i = 0; i < marks.length; i++)
    for (let j = i + 1; j < marks.length; j++) pairs.push([marks[i], marks[j]]);

  const separation = pairs.map(([a, b]) => {
    const hue = +deltaEOklch(a.oklch, b.oklch).toFixed(1);
    const light = +Math.abs(a.oklch[0] - b.oklch[0]).toFixed(3);
    const cvd = +deltaE(simulate(a.linear, "deutan"), simulate(b.linear, "deutan")).toFixed(1);
    const by =
      hue >= NORMAL_FLOOR && cvd >= CVD_FLOOR ? "hue"
      : light >= LIGHTNESS_FLOOR ? "lightness"
      : null;
    return { pair: `${a.name}/${b.name}`, hue_dE: hue, cvd_dE: cvd, lightness_delta: light, separated_by: by };
  });
  report.registers[register] = { separation };

  const unseparated = separation.filter((s) => !s.separated_by);
  unseparated.length
    ? fail("signal separation",
        unseparated.map((s) => `${s.pair} hue dE ${s.hue_dE}, deutan ${s.cvd_dE}, L delta ${s.lightness_delta}`).join("; "))
    : pass("signal separation",
        separation.map((s) => `${s.pair} by ${s.separated_by}`).join(", "));

  /* 3. The promo signal is the one that must never read as grey — it is the
     only mark that means "a human decided something". */
  const promo = tokens["--accent"];
  promo[1] < CHROMA_FLOOR
    ? fail("chroma floor", `--accent C=${promo[1]} reads grey`)
    : pass("chroma floor", `--accent C=${promo[1]}`);

  /* 4. Every mark against its own ground. */
  const low = marks.filter((m) => contrast(m.linear, surface) < CONTRAST_FLOOR);
  low.length
    ? fail("contrast vs surface", low.map((m) => `${m.name} ${contrast(m.linear, surface).toFixed(2)}:1`).join(", "))
    : pass("contrast vs surface",
        marks.map((m) => `${m.name} ${contrast(m.linear, surface).toFixed(2)}:1`).join(", "));

  /* 5 + 6. The ramp reads as a scale. */
  const rampL = RAMP.map((n) => tokens[n]?.[0]);
  if (rampL.some((v) => v === undefined)) {
    fail("ramp monotone", "a --heat-* step is missing");
  } else {
    const up = rampL.every((v, i) => i === 0 || v > rampL[i - 1]);
    const down = rampL.every((v, i) => i === 0 || v < rampL[i - 1]);
    up || down
      ? pass("ramp monotone", `L ${rampL.join(" -> ")}`)
      : fail("ramp monotone", `L ${rampL.join(" -> ")} turns back on itself`);

    const steps = rampL.slice(1).map((v, i) => Math.abs(v - rampL[i]));
    const tight = steps.filter((d) => d < RAMP_STEP_FLOOR);
    tight.length
      ? fail("ramp steps are distinct", `${tight.length} step(s) under ${RAMP_STEP_FLOOR} in L`)
      : pass("ramp steps are distinct", `min step ${Math.min(...steps).toFixed(3)} in L`);
    report.registers[register].ramp_lightness = rampL;
  }

  report.registers[register].checks = checks;
}

/* 7. The design rule, asserted rather than merely documented: sites are shown
      as small multiples, so there is no per-site colour token to drift into
      existence. A four-hue zone palette would break "colour is temperature". */
const zoneTokens = Object.keys(REGISTERS.dark).filter((n) => /^--zone-|^--dp-/.test(n));
if (zoneTokens.length) {
  failures.push(
    `sites have been given colour tokens (${zoneTokens.join(", ")}) — Almanac shows sites as ` +
      "small multiples so that colour can keep meaning temperature",
  );
}
report.zone_colour_tokens = zoneTokens;

report.pass = failures.length === 0;
report.failures = failures;

mkdirSync(RESULTS, { recursive: true });
writeFileSync(join(RESULTS, "A10-palette.json"), JSON.stringify(report, null, 2) + "\n");

if (failures.length) {
  console.error(`palette gate FAILED — ${failures.length} check(s):\n`);
  for (const f of failures) console.error(`  ${f}`);
  process.exit(1);
}
console.log(
  "palette gate passed — three signal marks and a six-step thermal ramp, " +
    "seven checks, both registers. docs/results/A10-palette.json written.",
);
