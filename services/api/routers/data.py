"""Provenance, sites and events — everything the Data tab reads."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.brand import load_brand
from services.api.data.registry import freshness
from services.api.deps import db

router = APIRouter(prefix="/data", tags=["data"])


@router.get(
    "/freshness", summary="What every dataset is, where it came from, and how much of it there is"
)
def get_freshness(conn: sqlite3.Connection = Depends(db)) -> dict:
    return freshness(conn)


@router.get("/zones", summary="The four SIDRA sites")
def get_zones() -> dict:
    brand = load_brand()
    return {
        "brand": {
            "name": brand.name,
            "name_ar": brand.name_ar,
            "fictional": brand.fictional,
            "disclaimer": brand.disclaimer,
        },
        "zones": [
            {
                "code": z.code,
                "name": z.name,
                "name_ar": z.name_ar,
                "site": z.site,
                "lat": z.lat,
                "lon": z.lon,
                "seats": z.seats,
                "outdoor_seats": z.outdoor_seats,
                "outdoor_share": round(z.outdoor_share, 3),
                "opens": z.opens,
                "closes": z.closes,
                "character": z.character,
                "demand_notes": z.demand_notes,
            }
            for z in brand.zones
        ],
    }


@router.get("/events", summary="Curated events, with distance to each site")
def get_events(
    conn: sqlite3.Connection = Depends(db),
    start: str | None = Query(None, description="ISO date, inclusive"),
    end: str | None = Query(None, description="ISO date, inclusive"),
    zone: str | None = Query(None, description="Return the distance to this site only"),
    limit: int = Query(200, ge=1, le=1000),
) -> dict:
    if zone and zone not in {z.code for z in load_brand().zones}:
        raise HTTPException(404, f"no site {zone!r}")

    sql = [
        "SELECT e.event_id, e.title, e.category, e.venue_name, e.start_date, e.end_date,",
        "e.days, e.scale, e.scale_weight, e.curated, e.date_confidence, e.source_url,",
        "e.wikipedia_url FROM events e",
    ]
    params: list = []
    where = []
    if start:
        where.append("e.end_date >= ?")
        params.append(start)
    if end:
        where.append("e.start_date <= ?")
        params.append(end)
    if where:
        sql.append("WHERE " + " AND ".join(where))
    sql.append("ORDER BY e.start_date LIMIT ?")
    params.append(limit)

    rows = [dict(r) for r in conn.execute(" ".join(sql), params)]
    ids = [r["event_id"] for r in rows]
    distances: dict[str, dict[str, float]] = {}
    if ids:
        q = f"SELECT event_id, zone_code, distance_km FROM event_zone_distance WHERE event_id IN ({','.join('?' * len(ids))})"
        dparams = list(ids)
        if zone:
            q += " AND zone_code = ?"
            dparams.append(zone)
        for d in conn.execute(q, dparams):
            distances.setdefault(d["event_id"], {})[d["zone_code"]] = d["distance_km"]

    for r in rows:
        r["distance_km"] = distances.get(r["event_id"], {})
        r["curated"] = bool(r["curated"])

    return {
        "count": len(rows),
        "events": rows,
        # Repeated in every response rather than assumed to be read once.
        "provenance": (
            "Curated from public listings. Series, venues and windows are real; "
            "the dates of a given edition are placed inside the established "
            "window and are not individually confirmed."
        ),
    }
