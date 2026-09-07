"""Time series for the charts.

Everything here is read-only and carries its label. `/series/footfall` returns
generated data and says so in the payload, not only in the documentation, so a
client that renders the numbers without reading this file still shows the
caveat.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

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
