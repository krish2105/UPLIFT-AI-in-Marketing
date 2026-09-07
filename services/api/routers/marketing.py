"""The marketing endpoints.

WHY THESE READ docs/results/ RATHER THAN FITTING ON REQUEST
-----------------------------------------------------------
Fitting four sites takes about ninety seconds. Doing that inside a request would
make the application unusable and would also make it dishonest in a subtler way:
the numbers on the Forecast tab would then be whatever the model happened to
produce at page load, and the figures in the report would be a different set
from a different fit.

So the evaluation numbers come from `docs/results/B*.json`, written by
`scripts/run_phase_b.py`, and the page shows the same numbers the report cites.
Only the FORWARD forecast — which has no evaluation attached and is genuinely a
function of today — is computed live, cached per site.
"""

from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.brand import load_brand
from services.api.deps import db
from services.api.marketing import allocator as alloc
from services.api.marketing import segments as seg
from services.api.marketing import uplift as up
from services.api.marketing.forecast import HORIZON_DAYS

router = APIRouter(prefix="/marketing", tags=["marketing"])
RESULTS = Path(__file__).resolve().parents[3] / "docs" / "results"


def _results(task: str) -> dict:
    path = RESULTS / f"{task}.json"
    if not path.exists():
        raise HTTPException(
            503,
            f"{task} has not been computed. Run `uv run python scripts/run_phase_b.py`. "
            "Nothing here fabricates a number when its measurement is missing.",
        )
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _forward_all() -> dict:
    """The precomputed horizon, read from docs/results/B1-forward.json.

    Fitting four sites takes about ninety seconds, so it happens in
    scripts/run_phase_b.py at build time and is served here as data. Fitting
    lazily on first request would charge the first visitor ninety seconds and
    would time out on a free instance; the horizon being as fresh as the last
    build is exactly right, because the series only moves when a pipeline runs.
    """
    return _results("B1-forward")["forward"]


@router.get("/forecast", summary="Evaluation against the baseline, and the forward horizon")
def get_forecast(
    conn: sqlite3.Connection = Depends(db),
    zone: str | None = Query(None),
    horizon: int = Query(HORIZON_DAYS, ge=1, le=56),
    include_forward: bool = Query(True),
) -> dict:
    zones = {z.code for z in load_brand().zones}
    if zone and zone not in zones:
        raise HTTPException(404, f"no site {zone!r}")

    payload = _results("B1-forecast")
    out = {
        "method": payload["method"],
        "generated_at": payload["generated_at"],
        "target_win_rate": payload["target_win_rate"],
        "win_rate": payload["win_rate"],
        "weeks_won": payload["weeks_won"],
        "weeks_total": payload["weeks_total"],
        "meets_target": payload["meets_target"],
        "note_on_smape": payload["note_on_smape"],
        "zones": {k: v for k, v in payload["zones"].items() if not zone or k == zone},
        "simulated": True,
    }

    if include_forward:
        precomputed = _forward_all()
        wanted = [zone] if zone else sorted(zones)
        # `horizon` trims the precomputed 56 days rather than refitting for a
        # shorter one — the same model, fewer rows returned.
        out["forward"] = {z: precomputed.get(z, [])[: horizon * 24] for z in wanted}
        out["horizon_days"] = horizon
    return out


@router.get("/segments", summary="RFM segments with a measured stability")
def get_segments() -> dict:
    payload = _results("B2-segments")
    return {**payload, "simulated": True}


@router.get("/segments/customers", summary="Per-customer RFM scores")
def get_customers(
    conn: sqlite3.Connection = Depends(db),
    limit: int = Query(200, ge=1, le=2000),
) -> dict:
    s = seg.rfm(conn)
    table = s.table.sort_values("monetary", ascending=False).head(limit)
    return {
        "as_of": s.as_of,
        "customers": json.loads(table.to_json(orient="records")),
        "sample": True,
    }


@router.get("/allocator", summary="Budget across channel x daypart")
def get_allocation(
    conn: sqlite3.Connection = Depends(db),
    budget: float = Query(12000, ge=500, le=200000),
) -> dict:
    payload = _results("B3-allocator")
    cells = alloc.build_cells(payload["daypart_demand_90d"])
    a = alloc.allocate(cells, budget)
    return {
        "budget": budget,
        "total_response": a.total_response,
        "marginal_spread": a.marginal_spread,
        "by_channel": {k: round(v, 2) for k, v in a.by_channel().items()},
        "by_daypart": {k: round(v, 2) for k, v in a.by_daypart().items()},
        "cells": [
            {
                "channel": c.channel,
                "label": alloc.CHANNEL_LABEL[c.channel],
                "daypart": c.daypart,
                "spend": c.spend,
                "response": round(c.response(), 2),
                "ceiling": c.ceiling,
            }
            for c in a.cells
        ],
        "sweep": payload["sweep"],
        "method": payload["method"],
        "assumed": True,
        "note": payload["note_on_parameters"],
    }


@router.get("/uplift", summary="Measured lift with its interval, bias and recovery evidence")
def get_uplift(
    conn: sqlite3.Connection = Depends(db),
    zone: str = Query("DXB-MAR"),
    start: str = Query("2026-06-01"),
    end: str = Query("2026-06-14"),
) -> dict:
    zones = {z.code for z in load_brand().zones}
    if zone not in zones:
        raise HTTPException(404, f"no site {zone!r}")

    payload = _results("B4-uplift")
    df = pd.read_sql_query(
        "SELECT substr(ts_local,1,10) d, zone_code, SUM(footfall) f "
        "FROM footfall_hourly GROUP BY d, zone_code",
        conn,
    )
    daily = df.pivot(index="d", columns="zone_code", values="f").dropna().astype(float)
    if start not in daily.index or end not in daily.index:
        raise HTTPException(400, "the window falls outside the loaded series")

    r = up.synthetic_control(daily, zone, start, end)
    bias = up.placebo_in_time(daily, zone, start, end)

    return {
        "treated": r.treated_zone,
        "window": [start, end],
        "weights": r.weights,
        "pre_rmse": r.pre_rmse,
        "lift_raw": r.lift_raw,
        "bias": round(bias, 4),
        "lift_adjusted": round(r.lift_raw - bias, 4),
        "ci": [r.ci_low_raw, r.ci_high_raw],
        "variance_reduction": r.variance_reduction,
        "placebo_p": r.placebo_p,
        "treated_total": r.treated_total,
        "counterfactual_total": r.counterfactual_total,
        "series": r.series,
        "recovery": payload["recovery"],
        "all_within_tolerance": payload["all_within_tolerance"],
        "worst_error_points": payload["worst_error_points"],
        "method": payload["method"],
        "note_on_bias": payload["note_on_bias"],
        "simulated": True,
    }


@router.get("/terrain", summary="Everything the 3D season view draws, in one call")
def terrain(
    conn: sqlite3.Connection = Depends(db),
    days: int = Query(56, ge=7, le=56),
) -> dict:
    """One payload, because the scene must not draw from four half-loaded fetches.

    A terrain that renders its blocks before its event bands arrive shows a
    reader a demand landscape with no reason attached to it, which is worse than
    an empty frame — so the view waits for this and draws once.

    The interval travels per day as [lo, hi] rather than as a single number. The
    cap on each block IS that interval, and a block whose forecast is uncertain
    has to look uncertain; a symmetric plus-or-minus would flatten exactly the
    asymmetry that matters at the low end, where demand is bounded by zero.
    """
    brand = load_brand()
    zones = [z.code for z in brand.zones]
    forward = _forward_all()

    # Hourly to daily. The interval does not sum: adding 24 hourly bands assumes
    # every hour misses in the same direction at once. Variances add, so the
    # half-widths combine in quadrature.
    lanes = []
    for code in zones:
        by_day: dict[str, dict[str, float]] = {}
        for row in forward.get(code, []):
            d = row["ts"][:10]
            cur = by_day.setdefault(d, {"yhat": 0.0, "half_sq": 0.0})
            cur["yhat"] += row["yhat"]
            half = (row["hi"] - row["lo"]) / 2
            cur["half_sq"] += half * half
        z = brand.zone(code)
        days_out = []
        for d, v in sorted(by_day.items())[:days]:
            half = v["half_sq"] ** 0.5
            days_out.append(
                {
                    "date": d,
                    "yhat": round(v["yhat"], 1),
                    "lo": round(max(0.0, v["yhat"] - half), 1),
                    "hi": round(v["yhat"] + half, 1),
                }
            )
        lanes.append(
            {
                "zone": code,
                "name": z.name,
                "lat": z.lat,
                "lon": z.lon,
                "outdoor_share": round(z.outdoor_share, 3),
                "days": days_out,
            }
        )

    horizon = [d["date"] for d in lanes[0]["days"]] if lanes else []
    start, end = (horizon[0], horizon[-1]) if horizon else (None, None)

    # Event bands cross every lane at once, which is what makes them bands
    # rather than per-site marks.
    bands = (
        [
            {
                "event_id": r["event_id"],
                "title": r["title"],
                "category": r["category"],
                "start": r["start_date"],
                "end": r["end_date"],
                "scale": r["scale"],
                "weight": r["scale_weight"],
                "venue": r["venue_name"],
                "curated": True,
            }
            for r in conn.execute(
                "SELECT event_id, title, category, start_date, end_date, scale, scale_weight, "
                "venue_name FROM events WHERE end_date >= ? AND start_date <= ? "
                "ORDER BY scale_weight DESC, start_date LIMIT 24",
                (start, end),
            )
        ]
        if horizon
        else []
    )

    # The weather ribbon runs along the ground plane, one value per day, taken
    # at the evening hours because that is when the terrace decision is made.
    #
    # It comes from the FORECAST's own assumed weather, not from the observation
    # table. Observations necessarily stop before the horizon begins — the first
    # version joined to them and returned an empty ribbon for every future day —
    # and showing a reader a different weather series from the one the model
    # used would be worse than showing none.
    ribbon_acc: dict[str, list[float]] = {}
    for row in forward.get("DXB-MAR", []):
        hour = int(row["ts"][11:13])
        if 17 <= hour <= 22 and row.get("apparent_c") is not None:
            ribbon_acc.setdefault(row["ts"][:10], []).append(row["apparent_c"])
    ribbon = [
        {"date": d, "apparent_c": round(sum(v) / len(v), 1)}
        for d, v in sorted(ribbon_acc.items())[:days]
    ]

    calendar = (
        [
            {
                "date": r["date_local"],
                "holiday": r["holiday_name"],
                "ramadan": bool(r["is_ramadan"]),
                "school_break": bool(r["is_school_break"]),
            }
            for r in conn.execute(
                "SELECT date_local, holiday_name, is_ramadan, is_school_break FROM calendar_days "
                "WHERE date_local BETWEEN ? AND ? AND "
                "(is_public_holiday = 1 OR is_ramadan = 1 OR is_school_break = 1) ORDER BY 1",
                (start, end),
            )
        ]
        if horizon
        else []
    )

    return {
        "horizon": horizon,
        "days": len(horizon),
        "lanes": lanes,
        "bands": bands,
        "ribbon": ribbon,
        "calendar": calendar,
        "simulated": True,
        "note": (
            "The cap on each block is its 80% prediction interval, so a forecast that is "
            "uncertain looks uncertain. Daily intervals combine in quadrature rather than "
            "summing: adding 24 hourly bands would assume every hour misses in the same "
            "direction at once."
        ),
        "ribbon_note": (
            "Evening apparent temperature as the forecast assumed it — the provider's "
            "16-day window, then climatology. Not the observation table, which stops "
            "before the horizon begins."
        ),
        "calendar_note": (
            "Public holidays, Ramadan days and school breaks falling inside the horizon. "
            "An empty list is a real answer: this window may simply contain none."
        ),
    }
