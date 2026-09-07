"""Dubai events: a curated series list expanded into dated instances.

WHY CURATED, AND WHAT THAT COSTS
--------------------------------
visitdubai.com/en/whats-on returns 403 to every non-browser client — checked on
2026-09-07 — and no public Dubai events feed exists with a licence that permits
redistribution. The master plan named the fallback in advance: a curated CSV
built by hand from public listings, labelled as such. This is it.

The honest shape of what that produces:

  REAL      the series, its venue, its coordinates, its category, and the
            calendar window it has occupied for years.
  DERIVED   the exact dates of any given edition. Those are placed inside the
            series' established window and carry
            date_confidence = 'annual_window'.

Nothing here is labelled as a verified date, `curated` is a column rather than
a footnote, and the API and the Data tab both surface it. A forecast feature
built on a date nobody checked should be visible as one.

WHY LONG SEASONS ARE SPLIT INTO MONTHS
--------------------------------------
Global Village runs from October to April. As a single row spanning 197 days it
is useless as a forecast feature — it would be "on" for more than half the
series and carry no information. Any run longer than 45 days is therefore split
into calendar-month segments, which is also how its demand actually behaves:
the opening weeks and the DSF overlap pull far harder than a Tuesday in March.

WIKIPEDIA ENRICHMENT
--------------------
Where a series has a Wikipedia article, its summary and canonical URL are
attached (CC BY-SA 4.0, attributed in docs/datasets.md and in the Data tab).
Requests are throttled and cached: the REST API 403s a default user agent and
429s a fast loop, both observed on 2026-09-07.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

from pipeline.common import RAW, USER_AGENT, Result  # noqa: E402
from services.api.brand import load_brand  # noqa: E402
from services.api.core.db import connect, upsert_many  # noqa: E402

SEED = RAW / "dubai_events_seed.yaml"
CSV_OUT = ROOT / "data" / "raw" / "dubai_events_24mo.csv"
WIKI_CACHE = RAW / "wikipedia_events.yaml"

HISTORY_DAYS = 760
HORIZON_DAYS = 400

#: Ordinal footfall pull, not an attendance estimate. An attendance number
#: would imply a source that does not exist.
SCALE_WEIGHT = {"small": 0.25, "medium": 0.5, "large": 0.75, "major": 1.0}

#: Runs longer than this are split into calendar-month segments. See the header.
MAX_SEGMENT_DAYS = 45

CURATED_LICENCE = (
    "Curated by the project from public listings; each row links the organiser's "
    "own page. Wikipedia summaries, where present, are CC BY-SA 4.0."
)

COLUMNS = (
    "event_id",
    "series_key",
    "title",
    "category",
    "venue_key",
    "venue_name",
    "lat",
    "lon",
    "start_date",
    "end_date",
    "days",
    "scale",
    "scale_weight",
    "curated",
    "date_confidence",
    "source_url",
    "licence",
    "wikipedia_title",
    "wikipedia_extract",
    "wikipedia_url",
    "segment_of",
)


class CoordinateError(ValueError):
    """A venue coordinate that cannot be in the UAE."""


#: The UAE's bounding box, generously drawn. Hatta sits at the eastern edge.
UAE_BOUNDS = (22.5, 26.6, 51.0, 56.6)  # lat_min, lat_max, lon_min, lon_max


def assert_in_uae(key: str, lat: float, lon: float) -> None:
    """Reject a coordinate outside the UAE.

    This exists because MAGNITUDE CANNOT CATCH A TRANSPOSITION HERE. Dubai sits
    near 25N 55E, so swapping latitude and longitude produces another plausible
    pair, and the distance between two swapped Dubai points comes out at 23 km
    against a correct 27 km — well inside anything a range check would accept.
    Measured, not assumed: see tests/data/test_events.py. The only reliable
    guard is a bounding box, applied at ingest.
    """
    lat_min, lat_max, lon_min, lon_max = UAE_BOUNDS
    if not (lat_min <= lat <= lat_max and lon_min <= lon <= lon_max):
        raise CoordinateError(
            f"venue {key!r} at ({lat}, {lon}) is outside the UAE — "
            "the usual cause is a transposed latitude and longitude"
        )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance. Over Dubai's scale the earth's curvature is
    irrelevant, but the formula costs nothing and removes a latitude-dependent
    error that a flat approximation would introduce."""
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _window_instances(window, start: date, end: date) -> list[tuple[date, date]]:
    """Expand a [month, day] window into one dated instance per year in range.

    A window whose end precedes its start wraps the year — Global Village opens
    in October and closes in April — so the end is taken in the following year.
    """
    (sm, sd), (em, ed) = window
    wraps = (sm, sd) > (em, ed)
    out: list[tuple[date, date]] = []
    for year in range(start.year - 1, end.year + 2):
        try:
            s = date(year, sm, sd)
            e = date(year + 1 if wraps else year, em, ed)
        except ValueError:
            continue  # 29 February in a non-leap year
        if e >= start and s <= end:
            out.append((s, e))
    return out


def _segments(s: date, e: date) -> list[tuple[date, date]]:
    """Split a long run into calendar-month segments; short runs pass through."""
    if (e - s).days + 1 <= MAX_SEGMENT_DAYS:
        return [(s, e)]
    out: list[tuple[date, date]] = []
    cur = s
    while cur <= e:
        nxt = date(cur.year + (cur.month == 12), (cur.month % 12) + 1, 1)
        out.append((cur, min(e, nxt - timedelta(days=1))))
        cur = nxt
    return out


def _calendar_anchors(conn) -> dict[str, list[tuple[date, date]]]:
    """Islamic-calendar events take their dates from the calendar pipeline
    rather than from a fixed window, because they move eleven days a year."""
    anchors: dict[str, list[tuple[date, date]]] = {
        "ramadan": [],
        "eid_al_fitr": [],
        "eid_al_adha": [],
    }
    ramadan_days = [
        date.fromisoformat(r[0])
        for r in conn.execute("SELECT date_local FROM calendar_days WHERE is_ramadan=1 ORDER BY 1")
    ]
    anchors["ramadan"] = _contiguous(ramadan_days)
    for key, name in (("eid_al_fitr", "Eid al-Fitr"), ("eid_al_adha", "Eid al-Adha")):
        days = [
            date.fromisoformat(r[0])
            for r in conn.execute(
                "SELECT date_local FROM calendar_days WHERE holiday_name=? ORDER BY 1", (name,)
            )
        ]
        anchors[key] = _contiguous(days)
    return anchors


def _contiguous(days: list[date]) -> list[tuple[date, date]]:
    """Collapse a sorted date list into (start, end) runs."""
    runs: list[tuple[date, date]] = []
    for d in days:
        if runs and (d - runs[-1][1]).days == 1:
            runs[-1] = (runs[-1][0], d)
        else:
            runs.append((d, d))
    return runs


def _wikipedia(titles: list[str], refresh: bool = False) -> dict[str, dict]:
    """Fetch article summaries, throttled and cached.

    The REST API 403s a default user agent and 429s a fast loop; both were
    observed on 2026-09-07. A descriptive agent and a pause per request is what
    the Wikimedia user-agent policy asks for.
    """
    cache: dict[str, dict] = {}
    if WIKI_CACHE.exists() and not refresh:
        cache = yaml.safe_load(WIKI_CACHE.read_text(encoding="utf-8")) or {}

    missing = [t for t in titles if t not in cache]
    for i, title in enumerate(missing):
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + title.replace(" ", "_")
        try:
            r = httpx.get(
                url,
                timeout=25.0,
                headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
                follow_redirects=True,
            )
            if r.status_code == 200:
                d = r.json()
                cache[title] = {
                    "title": d.get("title"),
                    "extract": (d.get("extract") or "")[:400],
                    "url": d.get("content_urls", {}).get("desktop", {}).get("page", ""),
                }
            else:
                cache[title] = {
                    "title": None,
                    "extract": "",
                    "url": "",
                    "note": f"HTTP {r.status_code}",
                }
        except httpx.HTTPError as exc:
            cache[title] = {"title": None, "extract": "", "url": "", "note": type(exc).__name__}
        if i < len(missing) - 1:
            time.sleep(1.1)  # courtesy, and the 429 threshold observed in testing

    if missing:
        WIKI_CACHE.write_text(
            yaml.safe_dump(cache, allow_unicode=True, sort_keys=True), encoding="utf-8"
        )
    return cache


def build(today: date | None = None, refresh: bool = False) -> tuple[list[tuple], list[tuple]]:
    seed = yaml.safe_load(SEED.read_text(encoding="utf-8"))
    venues, series = seed["venues"], seed["series"]
    brand = load_brand()
    conn = connect()

    today = today or date.today()
    start, end = today - timedelta(days=HISTORY_DAYS), today + timedelta(days=HORIZON_DAYS)
    anchors = _calendar_anchors(conn)
    wiki = _wikipedia(sorted({s["wikipedia"] for s in series if s.get("wikipedia")}), refresh)

    rows: list[tuple] = []
    distances: list[tuple] = []

    for key, v in venues.items():
        assert_in_uae(key, v["lat"], v["lon"])

    for s in series:
        venue = venues[s["venue"]]
        w = wiki.get(s.get("wikipedia") or "", {})

        if s.get("follows"):
            spans = [(a, b) for a, b in anchors[s["follows"]] if b >= start and a <= end]
            confidence = "calculated"  # inherits the calendar's moon-sighting caveat
        else:
            spans = _window_instances(s["window"], start, end)
            confidence = "annual_window"

        for span_start, span_end in spans:
            segs = _segments(span_start, span_end)
            parent = f"{s['key']}-{span_start.isoformat()}"
            for i, (a, b) in enumerate(segs):
                if b < start or a > end:
                    continue
                event_id = parent if len(segs) == 1 else f"{parent}-s{i + 1}"
                title = s["title"] if len(segs) == 1 else f"{s['title']} ({a.strftime('%B %Y')})"
                rows.append(
                    (
                        event_id,
                        s["key"],
                        title,
                        s["category"],
                        s["venue"],
                        venue["name"],
                        venue["lat"],
                        venue["lon"],
                        a.isoformat(),
                        b.isoformat(),
                        (b - a).days + 1,
                        s["scale"],
                        SCALE_WEIGHT[s["scale"]],
                        1,
                        confidence,
                        s["url"],
                        CURATED_LICENCE,
                        w.get("title"),
                        w.get("extract") or None,
                        w.get("url") or None,
                        parent if len(segs) > 1 else None,
                    )
                )
                for z in brand.zones:
                    distances.append(
                        (
                            event_id,
                            z.code,
                            round(haversine_km(venue["lat"], venue["lon"], z.lat, z.lon), 3),
                        )
                    )
    return rows, distances


def run(refresh: bool = False) -> dict:
    rows, distances = build(refresh=refresh)
    conn = connect()
    n = upsert_many(conn, "events", COLUMNS, rows)
    upsert_many(conn, "event_zone_distance", ("event_id", "zone_code", "distance_km"), distances)

    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        w.writerows(rows)
    return {"events": n, "distances": len(distances), "csv": str(CSV_OUT.relative_to(ROOT))}


def verify() -> int:
    brand = load_brand()
    conn = connect()
    r = Result(task="A6-events", dataset="events", generated_by="pipeline/events.py --verify")

    total = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    span = conn.execute("SELECT MIN(start_date) a, MAX(end_date) b FROM events").fetchone()
    r.stats = {
        "events": total,
        "series": conn.execute("SELECT COUNT(DISTINCT series_key) FROM events").fetchone()[0],
        "span": [span["a"], span["b"]],
        "by_category": {
            row["category"]: row["n"]
            for row in conn.execute(
                "SELECT category, COUNT(*) n FROM events GROUP BY category ORDER BY n DESC"
            )
        },
        "by_scale": {
            row["scale"]: row["n"]
            for row in conn.execute("SELECT scale, COUNT(*) n FROM events GROUP BY scale")
        },
        "date_confidence": {
            row["date_confidence"]: row["n"]
            for row in conn.execute(
                "SELECT date_confidence, COUNT(*) n FROM events GROUP BY date_confidence"
            )
        },
        "with_wikipedia": conn.execute(
            "SELECT COUNT(*) FROM events WHERE wikipedia_url IS NOT NULL"
        ).fetchone()[0],
    }

    r.check("at least 150 events over the window", total >= 150, f"{total} events")
    r.check(
        "every row is labelled curated",
        conn.execute("SELECT COUNT(*) FROM events WHERE curated!=1").fetchone()[0] == 0,
    )
    r.check(
        "no row claims a verified date",
        conn.execute(
            "SELECT COUNT(*) FROM events WHERE date_confidence NOT IN "
            "('annual_window','calculated')"
        ).fetchone()[0]
        == 0,
        "annual_window or calculated only",
    )
    r.check(
        "every row carries a source URL and a licence",
        conn.execute(
            "SELECT COUNT(*) FROM events WHERE source_url IS NULL OR source_url='' "
            "OR licence IS NULL OR licence=''"
        ).fetchone()[0]
        == 0,
    )
    r.check(
        "no event ends before it starts",
        conn.execute("SELECT COUNT(*) FROM events WHERE end_date < start_date").fetchone()[0] == 0,
    )
    r.check(
        f"no run longer than {MAX_SEGMENT_DAYS} days survives segmentation",
        conn.execute("SELECT COUNT(*) FROM events WHERE days > ?", (MAX_SEGMENT_DAYS,)).fetchone()[
            0
        ]
        == 0,
        "long seasons split into calendar months",
    )

    missing = conn.execute(
        "SELECT COUNT(*) FROM events e WHERE (SELECT COUNT(*) FROM event_zone_distance d "
        "WHERE d.event_id = e.event_id) != ?",
        (len(brand.zones),),
    ).fetchone()[0]
    r.check("every event has a distance to all four zones", missing == 0, f"{missing} incomplete")

    far = conn.execute("SELECT MAX(distance_km) FROM event_zone_distance").fetchone()[0]
    near = conn.execute("SELECT MIN(distance_km) FROM event_zone_distance").fetchone()[0]
    r.stats["distance_km_range"] = [near, far]
    # Hatta is about 130 km out and is the deliberate far edge; anything beyond
    # 150 km is not in the emirate and means a coordinate is wrong.
    r.check("distances are plausible for Dubai", far < 150, f"max {far} km")
    return r.report()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="refetch Wikipedia summaries")
    args = ap.parse_args()
    if not args.verify:
        meta = run(refresh=args.refresh)
        print(
            f"events: {meta['events']} instances, {meta['distances']} distances, csv at {meta['csv']}"
        )
        return 0
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
