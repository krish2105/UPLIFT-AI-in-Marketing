"use client";

import { LineChart, GroupedBars, ResponseChart, StatTile, ZONE_TOKEN, DAYPART_TOKEN, fmt } from "@/components/charts/Chart";
import type { DaypartResponse, FootfallResponse, WeatherResponse, Zone } from "@/lib/api";

/* The charts on the Season tab.
 *
 * Client components because they carry hover layers; the data is fetched on the
 * server and passed down, so the page renders complete without JavaScript and
 * the interaction is an enhancement rather than a requirement.
 */

const ZONE_ORDER = ["DXB-MAR", "DXB-DTN", "DXB-MOE", "DXB-DEI"];

export function SeasonCharts({
  footfall,
  dayparts,
  weather,
  zones,
}: {
  footfall: FootfallResponse;
  dayparts: DaypartResponse;
  weather: WeatherResponse;
  zones: Zone[];
}) {
  const name = Object.fromEntries(zones.map((z) => [z.code, z.name]));

  const dates = footfall.series[ZONE_ORDER[0]]?.map((p) => p.t) ?? [];
  const lineSeries = ZONE_ORDER.filter((z) => footfall.series[z]).map((z) => ({
    key: z,
    label: name[z] ?? z,
    token: ZONE_TOKEN[z],
    points: footfall.series[z].map((p, i) => ({ x: i, y: p.footfall })),
  }));
  const xTicks = dates
    .map((d, i) => ({ at: i, label: d.slice(5) }))
    .filter((_, i) => i % Math.ceil(dates.length / 6) === 0);

  const responseSeries = ZONE_ORDER.filter((z) => weather.by_zone[z]).map((z) => ({
    key: z,
    label: `${name[z] ?? z} · ${Math.round((weather.outdoor_share[z] ?? 0) * 100)}% outdoor`,
    token: ZONE_TOKEN[z],
    points: weather.by_zone[z].map((p) => ({ x: p.apparent_c, y: p.mean_footfall })),
  }));

  const totals = ZONE_ORDER.map((z) => ({
    zone: z,
    total: (footfall.series[z] ?? []).reduce((a, p) => a + p.footfall, 0),
  }));
  const busiest = totals.reduce((a, b) => (b.total > a.total ? b : a));
  const eveningShare = (() => {
    const all = Object.values(dayparts.by_zone);
    const evening = all.reduce((a, z) => a + (z.evening ?? 0), 0);
    const total = all.reduce((a, z) => a + Object.values(z).reduce((x, y) => x + y, 0), 0);
    return total ? evening / total : 0;
  })();

  return (
    <div className="stack-l">
      <div className="cards">
        <StatTile
          label="Busiest site, last 8 weeks"
          value={name[busiest.zone] ?? busiest.zone}
          detail={`${fmt(busiest.total)} visitors`}
          token={ZONE_TOKEN[busiest.zone]}
        />
        <StatTile
          label="Evening share of trade"
          value={`${Math.round(eveningShare * 100)}%`}
          detail="17:00 onward, all four sites"
          token="--dp-evening"
        />
        <StatTile
          label="Most weather-sensitive"
          value="Marina Walk"
          detail={`${Math.round((weather.outdoor_share["DXB-MAR"] ?? 0) * 100)}% of seats outdoors`}
          token="--dp-evening"
        />
        <StatTile
          label="Least weather-sensitive"
          value="Al Barsha"
          detail="fully enclosed — the control site"
          token="--dp-midday"
        />
      </div>

      <section className="stack">
        <h2 className="h3">Eight weeks of demand, per site</h2>
        <p className="note">
          Four sites on one axis, because they are the same measure. The shaded band is an
          illustrative ±12% interval; the Phase B forecast replaces it with a measured 80%
          prediction interval.
        </p>
        <LineChart
          series={lineSeries}
          band={0.12}
          xTicks={xTicks}
          caption="Daily footfall by site, generated"
          yLabel="visitors per day"
        />
      </section>

      <div className="split">
        <section className="stack">
          <h2 className="h3">Where the day happens</h2>
          <p className="note">
            The three bars are the three cells the media allocator optimises over. Deira runs on
            the early trade; Marina Walk lives after dark.
          </p>
          <GroupedBars
            groups={ZONE_ORDER.filter((z) => dayparts.by_zone[z]).map((z) => ({
              key: z,
              label: name[z] ?? z,
              values: dayparts.by_zone[z],
            }))}
            categories={dayparts.dayparts.map((d) => ({
              key: d,
              label: d,
              token: DAYPART_TOKEN[d] ?? "--text-faint",
            }))}
            caption="Footfall by daypart over 90 days, generated"
          />
        </section>

        <section className="stack">
          <h2 className="h3">The same weather, four answers</h2>
          <p className="note">{weather.note}</p>
          <ResponseChart
            series={responseSeries}
            caption="Evening footfall against apparent temperature"
            xLabel="apparent temperature, 2° bins"
            yLabel="mean visitors per hour"
          />
        </section>
      </div>
    </div>
  );
}
