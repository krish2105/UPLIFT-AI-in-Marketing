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
