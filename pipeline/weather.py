"""Weather for the four SIDRA sites: 24 months of history, plus the forecast.

WHAT THIS DATA IS, AND WHAT IT IS NOT
-------------------------------------
Open-Meteo's archive is ERA5 reanalysis on roughly an 11 km grid. Dubai is
small, so the four sites do not each get their own weather station — they land
in nearby grid cells and the spread between them is on the order of a degree.
That is recorded rather than hidden, and it matters for how the forecast is
read: the zones differ mainly in how they RESPOND to weather, not in what
weather they get. Marina Walk is more than half outdoor seating and Al Barsha
is fully enclosed; the same 41 degrees moves them in opposite directions. The
elasticity is the signal, not the temperature difference.

The archive lags real time by about five days, so history and forecast are
fetched from two endpoints and the boundary is recorded per row in `source`.

Licence: Open-Meteo data is CC BY 4.0, no key, no signup. Attribution is in
docs/datasets.md and in the application's Data tab.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from datetime import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

from pipeline.common import Result, fetch_json  # noqa: E402
from services.api.brand import load_brand  # noqa: E402
from services.api.core.db import connect, upsert_many  # noqa: E402

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
TZ = "Asia/Dubai"

HOURLY = "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m"

#: The archive is reanalysis and trails real time. Six days is comfortably
#: inside its lag; the forecast endpoint covers the gap and the horizon.
ARCHIVE_LAG_DAYS = 6
HISTORY_MONTHS = 24
FORECAST_DAYS = 16

COLUMNS = (
    "zone_code",
    "ts_local",
    "temp_c",
    "apparent_c",
    "humidity",
    "precip_mm",
    "wind_kmh",
    "source",
)


def _rows(payload: list[dict], zone_codes: list[str], source: str) -> list[tuple]:
    """Flatten Open-Meteo's column-oriented arrays into rows.

    The response is a list in the same order as the requested coordinates, which
    is the only thing tying a block of numbers back to a site — so the zone
    order is asserted by the caller rather than assumed here.
    """
    out: list[tuple] = []
    for zone_code, block in zip(zone_codes, payload, strict=True):
        h = block["hourly"]
        for i, ts in enumerate(h["time"]):
            out.append(
                (
                    zone_code,
                    ts,
                    h["temperature_2m"][i],
                    h["apparent_temperature"][i],
                    h["relative_humidity_2m"][i],
                    h["precipitation"][i],
                    h["wind_speed_10m"][i],
                    source,
                )
            )
    return out


def run(refresh: bool = False, today: date | None = None) -> dict:
    brand = load_brand()
    zones = list(brand.zones)
    codes = [z.code for z in zones]
    lats = ",".join(f"{z.lat}" for z in zones)
    lons = ",".join(f"{z.lon}" for z in zones)

    today = today or date.today()
    archive_end = today - timedelta(days=ARCHIVE_LAG_DAYS)
    archive_start = archive_end - timedelta(days=int(HISTORY_MONTHS * 30.44))

    history = fetch_json(
        ARCHIVE,
        {
            "latitude": lats,
            "longitude": lons,
            "start_date": archive_start.isoformat(),
            "end_date": archive_end.isoformat(),
            "hourly": HOURLY,
            "timezone": TZ,
        },
        cache_key="open-meteo-archive",
        refresh=refresh,
    )
    forecast = fetch_json(
        FORECAST,
        {
            "latitude": lats,
            "longitude": lons,
            "hourly": HOURLY,
            "timezone": TZ,
            "past_days": ARCHIVE_LAG_DAYS + 1,
            "forecast_days": FORECAST_DAYS,
        },
        cache_key="open-meteo-forecast",
        refresh=refresh,
    )

    conn = connect()
    written = 0
    # History first, then forecast: where they overlap the forecast endpoint's
    # recent-past values win, because they are the newer observation.
    written += upsert_many(conn, "weather_hourly", COLUMNS, _rows(history, codes, "archive"))
    written += upsert_many(conn, "weather_hourly", COLUMNS, _rows(forecast, codes, "forecast"))

    # The grid snap is the honest caveat, so it is measured rather than asserted.
    grid = [
        {"zone": c, "requested": [z.lat, z.lon], "grid_cell": [b["latitude"], b["longitude"]]}
        for c, z, b in zip(codes, zones, history, strict=True)
    ]
    return {
        "written": written,
        "grid": grid,
        "archive_span": [archive_start.isoformat(), archive_end.isoformat()],
    }


def verify(meta: dict | None = None) -> int:
    brand = load_brand()
    conn = connect()
    r = Result(
        task="A4-weather-etl", dataset="weather_hourly", generated_by="pipeline/weather.py --verify"
    )

    per_zone = {
        row["zone_code"]: row["n"]
        for row in conn.execute(
            "SELECT zone_code, COUNT(*) AS n FROM weather_hourly GROUP BY zone_code"
        )
    }
    span = conn.execute("SELECT MIN(ts_local) a, MAX(ts_local) b FROM weather_hourly").fetchone()
    total = sum(per_zone.values())

    r.stats = {
        "rows_total": total,
        "rows_per_zone": per_zone,
        "span_local": [span["a"], span["b"]],
        "sources": {
            row["source"]: row["n"]
            for row in conn.execute(
                "SELECT source, COUNT(*) AS n FROM weather_hourly GROUP BY source"
            )
        },
    }
    if meta:
        r.stats["grid_snap"] = meta["grid"]

    r.check(
        "all four zones present",
        set(per_zone) == {z.code for z in brand.zones},
        f"have {sorted(per_zone)}",
    )
    r.check(
        "at least 17000 hours per zone",
        bool(per_zone) and min(per_zone.values()) >= 17000,
        f"min {min(per_zone.values()) if per_zone else 0}",
    )

    # A gap in an hourly series silently becomes a missing feature row later, so
    # it is caught here rather than in the forecaster.
    worst = {}
    for code in per_zone:
        times = [
            row[0]
            for row in conn.execute(
                "SELECT ts_local FROM weather_hourly WHERE zone_code=? ORDER BY ts_local", (code,)
            )
        ]

        gaps = [
            (times[i - 1], times[i])
            for i in range(1, len(times))
            if (dt.fromisoformat(times[i]) - dt.fromisoformat(times[i - 1])).total_seconds()
            > 3 * 3600
        ]
        worst[code] = len(gaps)
    r.stats["gaps_over_3h"] = worst
    r.check("no gap longer than 3 hours", all(v == 0 for v in worst.values()), f"{worst}")

    nulls = conn.execute(
        "SELECT COUNT(*) FROM weather_hourly WHERE temp_c IS NULL OR apparent_c IS NULL"
    ).fetchone()[0]
    r.stats["null_temperatures"] = nulls
    r.check("no null temperatures", nulls == 0, f"{nulls} null rows")

    hot = conn.execute("SELECT MAX(temp_c) FROM weather_hourly").fetchone()[0]
    cold = conn.execute("SELECT MIN(temp_c) FROM weather_hourly").fetchone()[0]
    r.stats["temp_range_c"] = [cold, hot]
    # Dubai's records are roughly 6C and 52C. Anything outside that is a unit
    # or parsing error, not weather.
    r.check("temperatures are plausible for Dubai", cold >= 5 and hot <= 53, f"{cold}C to {hot}C")

    return r.report()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true", help="check the loaded data and write results")
    ap.add_argument("--refresh", action="store_true", help="ignore the raw cache and refetch")
    args = ap.parse_args()

    meta = None
    if not args.verify or args.refresh:
        meta = run(refresh=args.refresh)
        print(
            f"weather: {meta['written']:,} rows written, "
            f"archive {meta['archive_span'][0]} to {meta['archive_span'][1]}"
        )
    return verify(meta) if args.verify else 0


if __name__ == "__main__":
    raise SystemExit(main())
