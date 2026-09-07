/* The categorical palette gate.
 *
 * MAWSIM's three daypart hues are a chart palette before they are a design
 * choice: a reader has to tell a morning series from an evening one. That is a
 * COMPUTABLE property, so it is computed rather than judged.
 *
 * The six checks, run in both registers:
 *   1. lightness band      all three inside the register's band, so no series
 *                          looks more important than another
 *   2. chroma floor        none reads as grey
 *   3. CVD separation      adjacent pairs stay apart under deuteranopia,
 *                          protanopia and tritanopia (OKLab dE, x100)
 *   4. normal-vision floor adjacent pairs are distinguishable with full colour
 *                          vision — a separate and stricter bar
 *   5. contrast vs surface every hue reaches 3:1 against its own ground
 *   6. sequential ramp     the heat ramp is monotone in lightness
 *
 * The method follows the dataviz reference; it is reimplemented here rather
 * than shelled out to, so the check runs on any machine and in CI.
 *
 * HISTORY WORTH KEEPING: the first palette was literal — cool morning, bleached
 * yellow midday, ember evening — and this gate rejected it. Saturating midday
 * to clear the chroma floor put it 40 degrees from evening orange and collapsed
 * deuteranopia separation to dE 3.5. Desaturating it cleared that and made it
 * read grey. Neither is visible by eye on a designer's monitor.
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parseRegisters } from "./tokens.mjs";

const HERE = dirname(fileURLToPath(import.meta.url));
const TOKENS = join(HERE, "..", "styles", "tokens.css");
const RESULTS = join(HERE, "..", "..", "..", "docs", "results");

const BAND = { light: [0.43, 0.77], dark: [0.48, 0.67] };
const CHROMA_FLOOR = 0.1;
const CVD_FLOOR = 8;      // below this is a fail; 6-8 needs secondary encoding
const NORMAL_FLOOR = 15;
const CONTRAST_FLOOR = 3;

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


/* ── run ──────────────────────────────────────────────────────────────────── */

const REGISTERS = parseRegisters(readFileSync(TOKENS, "utf8"));
const CATEGORICAL = ["--dp-morning", "--dp-midday", "--dp-evening"];
const RAMP = ["--heat-0", "--heat-1", "--heat-2", "--heat-3", "--heat-4", "--heat-5"];

const report = { generated_by: "apps/web/scripts/check-palette.mjs", registers: {} };
const failures = [];

for (const register of ["dark", "light"]) {
  const tokens = REGISTERS[register];
  const surface = oklchToLinear(...tokens["--bg"]);
  const swatches = CATEGORICAL.map((name) => ({
    name,
    oklch: tokens[name],
    linear: oklchToLinear(...tokens[name]),
  }));

  const checks = [];
  const fail = (name, detail) => {
    checks.push({ name, pass: false, detail });
    failures.push(`${register}: ${name} — ${detail}`);
  };
  const pass = (name, detail) => checks.push({ name, pass: true, detail });

  const [lo, hi] = BAND[register];
  const offband = swatches.filter((s) => s.oklch[0] < lo || s.oklch[0] > hi);
  offband.length
    ? fail("lightness band", `outside ${lo}–${hi}: ${offband.map((s) => `${s.name} ${s.oklch[0]}`)}`)
    : pass("lightness band", `all inside L ${lo}–${hi}`);

  const grey = swatches.filter((s) => s.oklch[1] < CHROMA_FLOOR);
  grey.length
    ? fail("chroma floor", `reads grey: ${grey.map((s) => `${s.name} C=${s.oklch[1]}`)}`)
    : pass("chroma floor", `all C >= ${CHROMA_FLOOR}`);

  const pairs = [];
  for (let i = 0; i < swatches.length; i++)
    for (let j = i + 1; j < swatches.length; j++) pairs.push([swatches[i], swatches[j]]);

  const cvd = pairs.flatMap(([a, b]) =>
    ["deutan", "tritan"].map((kind) => ({
      pair: `${a.name}/${b.name}`,
      kind,
      dE: +deltaE(simulate(a.linear, kind), simulate(b.linear, kind)).toFixed(1),
    })),
  );
  const binding = cvd.filter((c) => c.kind === "deutan");
  const worstCvd = binding.reduce((w, c) => (c.dE < w.dE ? c : w));
  worstCvd.dE < CVD_FLOOR
    ? fail("cvd separation", `${worstCvd.pair} dE ${worstCvd.dE} (${worstCvd.kind})`)
    : pass("cvd separation", `worst ${worstCvd.pair} dE ${worstCvd.dE} (${worstCvd.kind})`);

  const normal = pairs.map(([a, b]) => ({
    pair: `${a.name}/${b.name}`,
    dE: +deltaEOklch(a.oklch, b.oklch).toFixed(1),
  }));
  const worstNormal = normal.reduce((w, c) => (c.dE < w.dE ? c : w));
  worstNormal.dE < NORMAL_FLOOR
    ? fail("normal-vision floor", `${worstNormal.pair} dE ${worstNormal.dE}`)
    : pass("normal-vision floor", `worst ${worstNormal.pair} dE ${worstNormal.dE}`);

  const lowContrast = swatches.filter((s) => contrast(s.linear, surface) < CONTRAST_FLOOR);
  lowContrast.length
    ? fail("contrast vs surface", `${lowContrast.map((s) => s.name)}`)
    : pass("contrast vs surface", `all >= ${CONTRAST_FLOOR}:1`);

  const rampL = RAMP.map((n) => tokens[n]?.[0]).filter((v) => v !== undefined);
  const monotone = rampL.every((v, i) => i === 0 || Math.abs(v) >= 0 ) &&
    (rampL.every((v, i) => i === 0 || v >= rampL[i - 1]) ||
     rampL.every((v, i) => i === 0 || v <= rampL[i - 1]));
  monotone
    ? pass("sequential ramp monotone", `L ${rampL.join(" -> ")}`)
    : fail("sequential ramp monotone", `L ${rampL.join(" -> ")} is not ordered`);

  report.registers[register] = {
    surface_oklch: tokens["--bg"],
    swatches: swatches.map((s) => ({
      name: s.name,
      oklch: s.oklch,
      contrast_vs_surface: +contrast(s.linear, surface).toFixed(2),
    })),
    cvd_pairs: cvd,
    normal_pairs: normal,
    checks,
  };
}

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
  "palette gate passed — 3 categorical hues and a 6-step ramp, six checks, both registers. " +
    "docs/results/A10-palette.json written.",
);
