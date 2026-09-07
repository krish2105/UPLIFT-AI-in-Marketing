/* The API client.
 *
 * Every response type carries the provenance fields the server sends —
 * `simulated`, `label`, `caveat`, `provenance` — because a component that
 * cannot see them cannot render them, and a chart that does not say what it is
 * showing is the failure mode this project exists to avoid.
 */

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Labelled = { label?: string; caveat?: string; simulated?: boolean };

export type Zone = {
  code: string;
  name: string;
  name_ar: string;
  site: string;
  lat: number;
  lon: number;
  seats: number;
  outdoor_seats: number;
  outdoor_share: number;
  opens: string;
  closes: string;
  character: string;
  demand_notes: string;
};

export type ZonesResponse = {
  brand: { name: string; name_ar: string; fictional: boolean; disclaimer: string };
  zones: Zone[];
};

export type DatasetSnapshot = {
  key: string;
  table: string;
  title: string;
  label: string;
  caveat: string;
  licence: string;
  source_name: string;
  source_url: string;
  verified: string;
  built_by: string;
  description: string;
  rows: number;
  span: [string, string] | null;
  present: boolean;
};

export type Freshness = {
  generated_at: string;
  datasets: DatasetSnapshot[];
  totals: { datasets: number; rows: number; by_label: Record<string, number> };
  standing_note: string;
};

export type SeriesPoint = { t: string; footfall: number; transactions: number };
export type FootfallResponse = Labelled & {
  grain: "hour" | "day";
  start: string;
  end: string;
  series: Record<string, SeriesPoint[]>;
};

export type DaypartResponse = {
  start: string;
  end: string;
  dayparts: string[];
  by_zone: Record<string, Record<string, number>>;
  simulated: boolean;
};

export type WeatherResponse = {
  hours: [number, number];
  by_zone: Record<string, { apparent_c: number; mean_footfall: number; n: number }[]>;
  outdoor_share: Record<string, number>;
  note: string;
  simulated: boolean;
};

export type EventRow = {
  event_id: string;
  title: string;
  category: string;
  venue_name: string;
  start_date: string;
  end_date: string;
  days: number;
  scale: string;
  scale_weight: number;
  curated: boolean;
  date_confidence: string;
  source_url: string;
  wikipedia_url: string | null;
  distance_km: Record<string, number>;
};

export type EventsResponse = { count: number; events: EventRow[]; provenance: string };

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function get<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    // The API is read-only and its data changes only when a pipeline runs, so
    // a short revalidation window costs nothing and keeps the page fast.
    next: { revalidate: 60 },
  });
  if (!res.ok) throw new ApiError(`${path} returned ${res.status}`, res.status);
  return (await res.json()) as T;
}

export type Station = {
  zone: string;
  ts: string | null;
  temp_c: number | null;
  humidity: number | null;
  wind_kmh: number | null;
  hijri: string;
  ramadan_day: number | null;
  index: number;
  pi: number;
  simulated: boolean;
};

export type WeeklyScore = {
  week: number;
  hours: number;
  mae_model: number;
  mae_baseline: number;
  won: boolean;
};

export type ZoneForecast = {
  mae: number;
  baseline_mae: number;
  improvement: number;
  smape: number;
  baseline_smape: number;
  weeks_won: number;
  weeks_total: number;
  win_rate: number;
  coverage_80: number;
  weekly: WeeklyScore[];
  top_drivers: Record<string, number>;
};

export type ForwardPoint = { ts: string; yhat: number; lo: number; hi: number; zone: string };

export type ForecastResponse = Labelled & {
  method: string;
  generated_at: string;
  target_win_rate: number;
  win_rate: number;
  weeks_won: number;
  weeks_total: number;
  meets_target: boolean;
  note_on_smape: string;
  zones: Record<string, ZoneForecast>;
  forward?: Record<string, ForwardPoint[]>;
  horizon_days?: number;
};

export type SegmentRow = {
  segment: string;
  customers: number;
  revenue: number;
  avg_basket: number;
  median_recency: number;
  median_frequency: number;
  revenue_share: number;
  customer_share: number;
  description: string;
};

export type SegmentsResponse = {
  method: string;
  as_of: string;
  customers: number;
  bootstrap_stability: number;
  segments: SegmentRow[];
  response_curves: {
    segment: string;
    customers: number;
    revenue_share: number;
    ceiling: number;
    saturation_rate: number;
    assumed: boolean;
  }[];
  curves_are_assumed: boolean;
  note_on_curves: string;
};

export type AllocCell = {
  channel: string;
  label: string;
  daypart: string;
  spend: number;
  response: number;
  ceiling: number;
};

export type AllocatorResponse = {
  budget: number;
  total_response: number;
  marginal_spread: number;
  by_channel: Record<string, number>;
  by_daypart: Record<string, number>;
  cells: AllocCell[];
  sweep: { budget: number; response: number; marginal_per_1000: number }[];
  method: string;
  assumed: boolean;
  note: string;
};

export type UpliftResponse = Labelled & {
  treated: string;
  window: [string, string];
  weights: Record<string, number>;
  pre_rmse: number;
  lift_raw: number;
  bias: number;
  lift_adjusted: number;
  ci: [number, number];
  variance_reduction: number;
  placebo_p: number;
  treated_total: number;
  counterfactual_total: number;
  series: { date: string; actual: number; counterfactual: number; in_promo: boolean }[];
  recovery: {
    injected: number;
    recovered_raw: number;
    bias: number;
    recovered: number;
    error_points: number;
    within_5_points: boolean;
  }[];
  all_within_tolerance: boolean;
  worst_error_points: number;
  method: string;
  note_on_bias: string;
};

export type Finding = {
  rule_id: string;
  family: string;
  severity: string;
  matched: string[];
  why: string;
  source_code: string;
  source_title: string;
  source_url: string;
  clause: string;
  clause_verified: boolean;
  clause_quote: string;
};

export type PersonaScore = {
  persona: string;
  name: string;
  total: number;
  criteria: Record<string, number>;
  note: string;
};

export type CreativeItem = {
  slot: string;
  lang: string;
  size: string;
  width: number;
  height: number;
  seed: string;
  zone: string;
  daypart: string;
  product: string;
  headline: string;
  body: string;
  cta: string;
  svg: string;
  compliance: { passed: boolean; checked_rules: number; citations: number; findings: Finding[] };
  panel: { mean: number; spread: number; scores: PersonaScore[]; simulated: boolean };
};

export type CreativesResponse = {
  count: number;
  creatives: CreativeItem[];
  passing: number;
  deterministic: boolean;
};

export type RuleRow = {
  id: string;
  family: string;
  severity: string;
  patterns: string[];
  rule_type: string;
  why: string;
  source: string;
  source_url: string;
  clause: string;
  clause_verified: boolean;
  clause_quote: string;
};

export type RulesResponse = {
  rules: RuleRow[];
  sources: Record<string, string>;
  deterministic: boolean;
  note: string;
};

export type GoldResponse = {
  cases: number;
  violations: number;
  clean: number;
  recall: number;
  precision: number;
  f1: number;
  missed: { text: string; expected: string; fired: string[] }[];
  false_alarms: { text: string; fired: string[] }[];
  target_recall: number;
};

export type ExperimentsResponse = {
  days: number;
  zone: string;
  by_zone: { zone: string; daily_mean: number; gap_sd: number; cv: number; mde: number; mde_pct: number; donors: string[] }[];
  sweep: { days: number; mde: number; mde_pct: number }[];
  method: string;
  note: string;
  simulated: boolean;
};

export type CrewResponse = {
  crew: { agent: string; tools: string[]; phase: string; output: string; reads: string; side_effects: string; note: string }[];
  side_effect_free: boolean;
  claim: string;
  publishing: string;
};

export type RedTeamCase = {
  id: string;
  control: string;
  attack: string;
  objective: string;
  held: boolean;
  /* An attack that succeeded and is carried as a stated limitation. It is still
     a break; `held` stays false. */
  accepted: boolean;
  detail: string;
};

export type SecurityResponse = {
  summary: { controls: number; by_status: Record<string, number>; enforced: number; coverage: number };
  controls: { id: string; risk: string; claim: string; evidence: string; status: string; verified_by: string }[];
  note: string;
  red_team?: {
    cases: number;
    held: number;
    broke: number;
    accepted_breaks: number;
    unaccepted_breaks: number;
    by_control: Record<string, { cases: number; held: number; accepted: number }>;
    generated_at: string;
    what_a_pass_means: string;
    known_limitation: string;
    results: RedTeamCase[];
  };
};

export type AskResponse = {
  query: string;
  answered: boolean;
  citations: { rank: number; id: string; score: number; text: string; source: string; source_url: string; kind: string }[];
  note: string;
  corpus_size: number;
};

export type TerrainDay = { date: string; yhat: number; lo: number; hi: number };

export type TerrainLane = {
  zone: string;
  name: string;
  lat: number;
  lon: number;
  outdoor_share: number;
  days: TerrainDay[];
};

export type TerrainBand = {
  event_id: string;
  title: string;
  category: string;
  start: string;
  end: string;
  scale: string;
  weight: number;
  venue: string;
  curated: boolean;
};

export type TerrainResponse = {
  horizon: string[];
  days: number;
  lanes: TerrainLane[];
  bands: TerrainBand[];
  ribbon: { date: string; apparent_c: number }[];
  calendar: { date: string; holiday: string | null; ramadan: boolean; school_break: boolean }[];
  simulated: boolean;
  note: string;
  ribbon_note: string;
  calendar_note: string;
};

export const api = {
  zones: () => get<ZonesResponse>("/data/zones"),
  freshness: () => get<Freshness>("/data/freshness"),
  events: (q = "") => get<EventsResponse>(`/data/events${q}`),
  footfall: (q = "") => get<FootfallResponse>(`/series/footfall${q}`),
  dayparts: (q = "") => get<DaypartResponse>(`/series/dayparts${q}`),
  weatherResponse: (q = "") => get<WeatherResponse>(`/series/weather-response${q}`),
  station: (zone = "DXB-MAR") => get<Station>(`/series/station?zone=${zone}`),
  forecast: (q = "") => get<ForecastResponse>(`/marketing/forecast${q}`),
  segments: () => get<SegmentsResponse>("/marketing/segments"),
  allocator: (budget = 12000) => get<AllocatorResponse>(`/marketing/allocator?budget=${budget}`),
  uplift: (q = "") => get<UpliftResponse>(`/marketing/uplift${q}`),
  creatives: (size = "square") => get<CreativesResponse>(`/creative/all?size=${size}`),
  rules: () => get<RulesResponse>("/compliance/rules"),
  gold: () => get<GoldResponse>("/compliance/gold"),
  experiments: (zone = "DXB-MAR", days = 14) =>
    get<ExperimentsResponse>(`/experiments?zone=${zone}&days=${days}`),
  crew: () => get<CrewResponse>("/crew"),
  security: () => get<SecurityResponse>("/security"),
  ask: (q: string, k = 4) => get<AskResponse>(`/ask?q=${encodeURIComponent(q)}&k=${k}`),
  terrain: (days = 56) => get<TerrainResponse>(`/marketing/terrain?days=${days}`),
};

/** Fetch without throwing, so a page can render an honest "API unreachable"
 *  state instead of a Next error overlay. The deployed API sleeps after 15
 *  minutes idle, and that is a normal condition rather than a bug. */
export async function tryFetch<T>(fn: () => Promise<T>): Promise<{ data: T } | { error: string }> {
  try {
    return { data: await fn() };
  } catch (e) {
    return { error: e instanceof Error ? e.message : String(e) };
  }
}
