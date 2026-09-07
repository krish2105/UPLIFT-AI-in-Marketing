"""Experiments, the crew registry, the security scorecard, and Ask."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from services.api.brand import load_brand
from services.api.deps import db
from services.api.marketing import experiments
from services.api.rag import corpus
from services.api.security.scorecard import Scorecard

router = APIRouter(tags=["system"])

#: The crew, and the single claim the whole safety argument rests on: the
#: side-effects column is "none" on every row, and it is asserted over the whole
#: registry by a test rather than reviewed by eye.
CREW: tuple[dict, ...] = (
    {
        "agent": "Forecaster",
        "tools": ["query_sql", "forecast"],
        "phase": "B",
        "output": "Eight-week demand per site with an 80% interval",
        "reads": "footfall, weather, calendar, events",
        "side_effects": "none",
        "note": "The forecast itself is computed in code; the agent selects and explains it.",
    },
    {
        "agent": "Planner",
        "tools": ["forecast_lookup", "allocate_budget"],
        "phase": "B",
        "output": "Promo calendar with a channel x daypart split",
        "reads": "the forecast and the allocator",
        "side_effects": "none",
        "note": "Sizes a promotion to the forecast's LOWER bound, not its point estimate.",
    },
    {
        "agent": "Creative",
        "tools": ["ask", "generate_variants"],
        "phase": "C",
        "output": "Three variants per slot, per language",
        "reads": "the brand kit",
        "side_effects": "none",
        "note": "Composition is deterministic; Phase C's model writes the copy, not the artefact.",
    },
    {
        "agent": "Compliance",
        "tools": ["ask", "check_rules"],
        "phase": "C",
        "output": "Pass or fail with the clause each finding came from",
        "reads": "the rule set and the corpus",
        "side_effects": "none",
        "note": "The verdict is regex, not inference. A model cannot talk it into a pass.",
    },
    {
        "agent": "Panel",
        "tools": ["simulate_personas"],
        "phase": "C",
        "output": "Five scores and a spread",
        "reads": "the creative",
        "side_effects": "none",
        "note": "A filter, not customer research. Deterministic under seed.",
    },
    {
        "agent": "Measurer",
        "tools": ["query_sql", "uplift"],
        "phase": "B",
        "output": "Lift with an interval, a placebo p and the estimator's own bias",
        "reads": "footfall",
        "side_effects": "none",
        "note": "Reports the bias it measures on a window where nothing happened.",
    },
    {
        "agent": "Auditor",
        "tools": ["flag_run"],
        "phase": "C",
        "output": "Policy findings: uncited claims, budget breaches, creatives that slipped",
        "reads": "every other agent's output",
        "side_effects": "none",
        "note": "Flags. It cannot block, revise or publish — a person does that.",
    },
)


@router.get("/experiments", summary="Minimum detectable effect, per site and per window")
def get_experiments(
    conn: sqlite3.Connection = Depends(db),
    zone: str = Query("DXB-MAR"),
    days: int = Query(14, ge=1, le=90),
) -> dict:
    if zone not in {z.code for z in load_brand().zones}:
        raise HTTPException(404, f"no site {zone!r}")

    designs = experiments.all_zones(conn, days)
    return {
        "days": days,
        "zone": zone,
        "by_zone": [
            {
                "zone": d.zone,
                "daily_mean": d.daily_mean,
                "gap_sd": d.daily_sd,
                "cv": d.cv,
                "mde": d.mde,
                "mde_pct": round(d.mde_pct, 2),
                "donors": d.donors,
            }
            for d in designs
        ],
        "sweep": experiments.sweep(conn, zone),
        "method": (
            "Minimum detectable effect at 95% confidence and 80% power. The noise that "
            "matters is the variability of the GAP between the site and its synthetic "
            "control, not the site's own variability — a volatile site is still cheap to "
            "measure if its control is volatile in the same way."
        ),
        "note": (
            "Decided BEFORE the promotion, or not at all. If a promotion is not expected "
            "to clear the MDE for its window, it should run longer or not be measured — "
            "running it and reporting whatever number comes out is what this page exists "
            "to prevent."
        ),
        "simulated": True,
    }


@router.get("/crew", summary="Every agent, its tools, and its side effects")
def get_crew() -> dict:
    return {
        "crew": list(CREW),
        "side_effect_free": all(a["side_effects"] == "none" for a in CREW),
        "claim": (
            "No agent has a tool that reaches the outside world. The column reads 'none' on "
            "every row, and that is asserted over the whole registry by a test rather than "
            "reviewed by eye — so a tool added tomorrow with a side effect fails the build."
        ),
        "publishing": (
            "Exporting a campaign is a human action taken outside this application. There is "
            "no endpoint that sends, schedules or publishes anything."
        ),
    }


@router.get("/security", summary="The OWASP ASI scorecard")
def get_security() -> dict:
    return Scorecard().as_dict()


@router.get("/ask", summary="Cited retrieval over the project's own corpus")
def get_ask(
    q: str = Query(..., min_length=2, max_length=300), k: int = Query(4, ge=1, le=10)
) -> dict:
    return corpus.answer(q, k)
