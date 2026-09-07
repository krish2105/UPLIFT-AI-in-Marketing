/* Fixed demo data for the design-comparison page.
 *
 * Every value here is INVENTED for the purpose of showing a component at a
 * realistic density, and the page says so on screen. Nothing on /design comes
 * from the forecast pipeline, because the pipeline does not exist yet at this
 * point in the build and a design review that silently shows made-up numbers
 * as if they were results is how a project starts lying to itself.
 */

export type Zone = {
  code: string;
  name: string;
  nameAr: string;
  /** Forecast demand index, 1.00 = the zone's own trailing median. */
  index: number;
  /** Half-width of the 80% prediction interval, in index points. */
  pi: number;
  /** Forecast max temperature, °C. */
  tempC: number;
  /** Hourly forecast shape for the next 24h, normalised 0..1. */
  shape: number[];
  character: string;
};

/** SIDRA's four sites. The shapes are bimodal, and differently so per zone —
 *  Deira wakes early, Marina lives after dark. That difference is the reason
 *  the application forecasts per zone instead of per brand. */
export const ZONES: Zone[] = [
  {
    code: "DXB-MAR",
    name: "Marina Walk",
    nameAr: "مرسى دبي",
    index: 1.42,
    pi: 0.19,
    tempC: 39,
    character: "outdoor seating · weather-elastic",
    shape: [
      0.04, 0.03, 0.02, 0.02, 0.05, 0.14, 0.31, 0.48, 0.52, 0.41, 0.33, 0.3, 0.31, 0.29, 0.26,
      0.28, 0.37, 0.58, 0.79, 0.94, 1.0, 0.88, 0.62, 0.28,
    ],
  },
  {
    code: "DXB-DTN",
    name: "Downtown",
    nameAr: "وسط المدينة",
    index: 1.18,
    pi: 0.09,
    tempC: 41,
    character: "tourist-heavy · event-elastic",
    shape: [
      0.06, 0.04, 0.03, 0.03, 0.06, 0.16, 0.38, 0.62, 0.71, 0.63, 0.55, 0.54, 0.58, 0.55, 0.49,
      0.5, 0.58, 0.72, 0.86, 0.93, 0.9, 0.76, 0.52, 0.24,
    ],
  },
  {
    code: "DXB-MOE",
    name: "Al Barsha",
    nameAr: "البرشاء",
    index: 0.96,
    pi: 0.07,
    tempC: 41,
    character: "indoor · weather-inelastic",
    shape: [
      0.02, 0.02, 0.01, 0.01, 0.03, 0.09, 0.24, 0.44, 0.56, 0.58, 0.57, 0.62, 0.68, 0.66, 0.61,
      0.63, 0.7, 0.78, 0.83, 0.8, 0.7, 0.55, 0.34, 0.12,
    ],
  },
  {
    code: "DXB-DEI",
    name: "Deira",
    nameAr: "ديرة",
    index: 0.81,
    pi: 0.14,
    tempC: 40,
    character: "value segment · early peak",
    shape: [
      0.08, 0.06, 0.05, 0.07, 0.18, 0.42, 0.71, 0.88, 0.82, 0.66, 0.52, 0.46, 0.44, 0.4, 0.36,
      0.38, 0.45, 0.56, 0.64, 0.66, 0.58, 0.44, 0.26, 0.12,
    ],
  },
];

export const CREATIVE = {
  zone: "DXB-MAR",
  slot: "Eid al-Adha weekend · evening daypart",
  headline: "Evenings are back on the Walk.",
  body: "Cardamom cold brew and pistachio knafeh, from 17:00. Marina Walk only.",
  cta: "Find your table",
  panel: 7.2,
  panelN: 5,
  seed: 20260907,
};

export const COMPLIANCE = [
  {
    id: "SID-N-004",
    verdict: "fail" as const,
    claim: "“Sugar-free” on the date-syrup latte",
    rule: "Nutrition claim requires the product to contain no more than 0.5 g sugars per 100 ml.",
    source: "Codex CAC/GL 23-1997 §3.1",
    citations: 2,
  },
  {
    id: "SID-B-011",
    verdict: "pass" as const,
    claim: "“From 17:00. Marina Walk only.”",
    rule: "Offer scope and location stated. No unsubstantiated superlative.",
    source: "SIDRA brand guidelines §4.2",
    citations: 1,
  },
];

export const FRESHNESS = [
  { name: "weather_hourly", rows: "70,128", span: "2024-09 → 2026-09", label: "observed", licence: "CC BY 4.0" },
  { name: "events_curated", rows: "163", span: "2024-09 → 2026-09", label: "curated", licence: "mixed, per row" },
  { name: "footfall_hourly", rows: "70,128", span: "2024-09 → 2026-09", label: "simulated", licence: "generated" },
  { name: "pos_baskets", rows: "9,540", span: "2025-09 → 2026-09", label: "sample", licence: "generated" },
];
