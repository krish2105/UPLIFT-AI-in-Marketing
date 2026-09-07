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
from services.api.marketing.forecast import HORIZON_DAYS, forward

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


@lru_cache(maxsize=8)
def _forward_cached(zone: str, days: int, stamp: str) -> str:
    """`stamp` is the latest loaded hour: it makes the cache key move when the
    data does, so a refreshed pipeline is not served a stale horizon."""
    from services.api.core.db import connect

    df = forward(connect(), zone, days)
    return df.to_json(orient="records", date_format="iso")


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
        stamp = conn.execute("SELECT MAX(ts_local) FROM footfall_hourly").fetchone()[0]
        wanted = [zone] if zone else sorted(zones)
        out["forward"] = {z: json.loads(_forward_cached(z, horizon, stamp)) for z in wanted}
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
