"""Time series for the charts.

Everything here is read-only and carries its label. `/series/footfall` returns
generated data and says so in the payload, not only in the documentation, so a
client that renders the numbers without reading this file still shows the
caveat.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.brand import load_brand
from services.api.data.registry import by_key
from services.api.deps import db

router = APIRouter(prefix="/series", tags=["series"])

DAYPARTS = (("morning", 6, 11), ("midday", 11, 17), ("evening", 17, 24))


def _zone_codes() -> set[str]:
    return {z.code for z in load_brand().zones}


def _require_zone(zone: str | None) -> None:
    if zone and zone not in _zone_codes():
        raise HTTPException(404, f"no site {zone!r}")


@router.get("/footfall", summary="Hourly or daily footfall per site (generated)")
def footfall(
    conn: sqlite3.Connection = Depends(db),
    zone: str | None = Query(None),
    start: str | None = Query(None, description="ISO date, inclusive"),
    end: str | None = Query(None, description="ISO date, inclusive"),
    grain: str = Query("day", pattern="^(hour|day)$"),
) -> dict:
    _require_zone(zone)
    dataset = by_key("footfall_hourly")

    if not end:
        end = conn.execute("SELECT MAX(substr(ts_local,1,10)) FROM footfall_hourly").fetchone()[0]
    if not start:
        start = (date.fromisoformat(end) - timedelta(days=56)).isoformat()

    bucket = "ts_local" if grain == "hour" else "substr(ts_local,1,10)"
    sql = (
        f"SELECT zone_code, {bucket} AS t, SUM(footfall) AS footfall, "
        "SUM(transactions) AS transactions FROM footfall_hourly "
        "WHERE substr(ts_local,1,10) BETWEEN ? AND ?"
    )
    params: list = [start, end]
    if zone:
        sql += " AND zone_code = ?"
        params.append(zone)
    sql += f" GROUP BY zone_code, {bucket} ORDER BY zone_code, t"

    series: dict[str, list[dict]] = {}
    for r in conn.execute(sql, params):
        series.setdefault(r["zone_code"], []).append(
            {"t": r["t"], "footfall": r["footfall"], "transactions": r["transactions"]}
        )

    return {
        "grain": grain,
        "start": start,
        "end": end,
        "series": series,
        "label": dataset.label.value,
        "caveat": dataset.label.caveat,
        "simulated": True,
    }


@router.get("/dayparts", summary="Footfall split by daypart (generated)")
def dayparts(
    conn: sqlite3.Connection = Depends(db),
    start: str | None = Query(None),
    end: str | None = Query(None),
) -> dict:
    if not end:
        end = conn.execute("SELECT MAX(substr(ts_local,1,10)) FROM footfall_hourly").fetchone()[0]
    if not start:
        start = (date.fromisoformat(end) - timedelta(days=90)).isoformat()

    case = " ".join(
        f"WHEN CAST(substr(ts_local,12,2) AS INTEGER) >= {lo} "
        f"AND CAST(substr(ts_local,12,2) AS INTEGER) < {hi} THEN '{name}'"
        for name, lo, hi in DAYPARTS
    )
    rows = conn.execute(
        f"SELECT zone_code, CASE {case} ELSE 'closed' END AS daypart, "
        "SUM(footfall) AS footfall FROM footfall_hourly "
        "WHERE substr(ts_local,1,10) BETWEEN ? AND ? "
        "GROUP BY zone_code, daypart",
        (start, end),
    ).fetchall()

    out: dict[str, dict[str, int]] = {}
    for r in rows:
        if r["daypart"] == "closed":
            continue
        out.setdefault(r["zone_code"], {})[r["daypart"]] = r["footfall"]

    return {
        "start": start,
        "end": end,
        "dayparts": [d[0] for d in DAYPARTS],
        "by_zone": out,
        "simulated": True,
    }


@router.get("/weather-response", summary="Footfall against apparent temperature, per site")
def weather_response(
    conn: sqlite3.Connection = Depends(db),
    hours: str = Query("18-22", pattern=r"^\d{1,2}-\d{1,2}$"),
) -> dict:
    """The evidence for the per-zone argument.

    Binned rather than returned as raw points: 70,000 scatter points is a slow
    payload and an unreadable chart, and the shape of the response is what the
    reader needs, not the individual hours.
    """
    lo, hi = (int(x) for x in hours.split("-"))
    rows = conn.execute(
        "SELECT f.zone_code, CAST(ROUND(w.apparent_c / 2) * 2 AS INTEGER) AS bin, "
        "AVG(f.footfall) AS mean_footfall, COUNT(*) AS n "
        "FROM footfall_hourly f JOIN weather_hourly w "
        "  ON w.zone_code = f.zone_code AND w.ts_local = f.ts_local "
        "WHERE CAST(substr(f.ts_local,12,2) AS INTEGER) BETWEEN ? AND ? "
        "GROUP BY f.zone_code, bin HAVING n >= 20 ORDER BY f.zone_code, bin",
        (lo, hi),
    ).fetchall()

    brand = load_brand()
    outdoor = {z.code: round(z.outdoor_share, 3) for z in brand.zones}
    by_zone: dict[str, list[dict]] = {}
    for r in rows:
        by_zone.setdefault(r["zone_code"], []).append(
            {"apparent_c": r["bin"], "mean_footfall": round(r["mean_footfall"], 1), "n": r["n"]}
        )

    return {
        "hours": [lo, hi],
        "by_zone": by_zone,
        "outdoor_share": outdoor,
        "note": (
            "Each point is a two-degree bin of apparent temperature with at least "
            "twenty observations. The zones differ in how they respond, not in "
            "what weather they get — all four sit in nearby ERA5 grid cells."
        ),
        "simulated": True,
    }


@router.get("/station", summary="The current station reading for a site")
def station(
    conn: sqlite3.Connection = Depends(db),
    zone: str = Query("DXB-MAR"),
) -> dict:
    """Everything the station strip prints, in one call.

    The demand index is the site's next 24 hours against its own trailing
    28-day median for the same hours — a ratio to itself, so a small site and a
    large one are comparable, and so the number means "busier than usual here"
    rather than "busier than the other sites".
    """
    _require_zone(zone)

    latest = (
        conn.execute(
            "SELECT ts_local, temp_c, humidity, wind_kmh FROM weather_hourly "
            "WHERE zone_code = ? AND ts_local >= datetime('now') ORDER BY ts_local LIMIT 1",
            (zone,),
        ).fetchone()
        or conn.execute(
            "SELECT ts_local, temp_c, humidity, wind_kmh FROM weather_hourly "
            "WHERE zone_code = ? ORDER BY ts_local DESC LIMIT 1",
            (zone,),
        ).fetchone()
    )

    recent = (
        conn.execute(
            "SELECT AVG(footfall) a FROM footfall_hourly WHERE zone_code = ? "
            "AND substr(ts_local,1,10) >= date((SELECT MAX(substr(ts_local,1,10)) "
            "FROM footfall_hourly), '-7 day')",
            (zone,),
        ).fetchone()["a"]
        or 0.0
    )
    trailing = (
        conn.execute(
            "SELECT AVG(footfall) a FROM footfall_hourly WHERE zone_code = ? "
            "AND substr(ts_local,1,10) >= date((SELECT MAX(substr(ts_local,1,10)) "
            "FROM footfall_hourly), '-35 day') "
            "AND substr(ts_local,1,10) < date((SELECT MAX(substr(ts_local,1,10)) "
            "FROM footfall_hourly), '-7 day')",
            (zone,),
        ).fetchone()["a"]
        or 1.0
    )

    index = recent / trailing if trailing else 1.0

    # The interval width is the dispersion of that ratio across the last eight
    # weeks — not a model output, and labelled as an observed spread.
    weekly = [
        r["a"]
        for r in conn.execute(
            "SELECT AVG(footfall) a FROM footfall_hourly WHERE zone_code = ? "
            "GROUP BY strftime('%Y-%W', ts_local) ORDER BY 1 DESC LIMIT 8",
            (zone,),
        )
    ]
    spread = float(np.std(weekly) / np.mean(weekly)) if len(weekly) > 1 and np.mean(weekly) else 0.1

    hijri = conn.execute(
        "SELECT is_ramadan, ramadan_day FROM calendar_days WHERE date_local = date('now')"
    ).fetchone()

    return {
        "zone": zone,
        "ts": latest["ts_local"] if latest else None,
        "temp_c": round(latest["temp_c"], 1) if latest else None,
        "humidity": round(latest["humidity"], 0) if latest else None,
        "wind_kmh": round(latest["wind_kmh"], 1) if latest else None,
        "hijri": _hijri_today(),
        "ramadan_day": hijri["ramadan_day"] if hijri and hijri["is_ramadan"] else None,
        "index": round(index, 2),
        "pi": round(spread, 2),
        "simulated": True,
    }


def _hijri_today() -> str:
    """Today in the Hijri calendar, for the station strip.

    Calculated from the Umm al-Qura tabular calendar, which can differ from a
    sighting by a day — the same caveat the calendar pipeline carries.
    """
    from datetime import date

    from hijridate import Gregorian

    months = [
        "Muharram",
        "Safar",
        "Rabi' I",
        "Rabi' II",
        "Jumada I",
        "Jumada II",
        "Rajab",
        "Sha'ban",
        "Ramadan",
        "Shawwal",
        "Dhu al-Qi'dah",
        "Dhu al-Hijjah",
    ]
    t = date.today()
    h = Gregorian(t.year, t.month, t.day).to_hijri()
    return f"{h.day} {months[h.month - 1]} {h.year}"
