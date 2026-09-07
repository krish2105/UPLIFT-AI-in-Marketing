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

export const api = {
  zones: () => get<ZonesResponse>("/data/zones"),
  freshness: () => get<Freshness>("/data/freshness"),
  events: (q = "") => get<EventsResponse>(`/data/events${q}`),
  footfall: (q = "") => get<FootfallResponse>(`/series/footfall${q}`),
  dayparts: (q = "") => get<DaypartResponse>(`/series/dayparts${q}`),
  weatherResponse: (q = "") => get<WeatherResponse>(`/series/weather-response${q}`),
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
