"""Produce every Phase B number, and write it where a document can cite it.

Nothing in this project quotes a figure it did not measure, so this is the only
route a marketing result takes into a report or onto a page. Re-run it and every
number downstream moves with it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

from pipeline.common import now_iso  # noqa: E402
from services.api.brand import load_brand  # noqa: E402
from services.api.core.db import connect  # noqa: E402
from services.api.marketing import allocator, segments, uplift  # noqa: E402
from services.api.marketing.features import load_frame  # noqa: E402
from services.api.marketing.forecast import HORIZON_DAYS, evaluate, forward  # noqa: E402

RESULTS = ROOT / "docs" / "results"
WIN_RATE_TARGET = 0.70
RECOVERY_TOLERANCE = 0.05


def write(name: str, payload: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    path = RESULTS / f"{name}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"  wrote {path.relative_to(ROOT)}")
    return path


def b1_forecast(conn) -> dict:
    print("B1 forecast — fitting four sites against a seasonal-naive baseline")
    zones = [z.code for z in load_brand().zones]
    results = {}
    for zone in zones:
        r = evaluate(load_frame(conn, zone))
        results[zone] = {
            "mae": r.mae,
            "baseline_mae": r.baseline_mae,
            "improvement": round(r.improvement, 4),
            "smape": r.smape,
            "baseline_smape": r.baseline_smape,
            "weeks_won": r.weeks_won,
            "weeks_total": r.weeks_total,
            "win_rate": round(r.win_rate, 4),
            "coverage_80": r.coverage_80,
            "weekly": r.weekly,
            "top_drivers": dict(list(r.importances.items())[:8]),
        }
        print(
            f"    {zone}  MAE {r.mae:>6.2f} vs {r.baseline_mae:>6.2f}  "
            f"({r.improvement:+.1%})  weeks {r.weeks_won}/{r.weeks_total}"
        )

    overall_won = sum(v["weeks_won"] for v in results.values())
    overall_total = sum(v["weeks_total"] for v in results.values())
    return {
        "task": "B1-forecast",
        "generated_by": "scripts/run_phase_b.py",
        "generated_at": now_iso(),
        "method": (
            "GradientBoostingRegressor with absolute-error loss for the median and "
            "pinball loss at the 10th and 90th percentiles for the interval. "
            "Chronological holdout of 56 days; the baseline is seasonal naive — the "
            "same hour, same weekday, last week."
        ),
        "target_win_rate": WIN_RATE_TARGET,
        "win_rate": round(overall_won / overall_total, 4),
        "weeks_won": overall_won,
        "weeks_total": overall_total,
        "meets_target": overall_won / overall_total >= WIN_RATE_TARGET,
        "note_on_smape": (
            "sMAPE is higher for the model than for the baseline on every site, and "
            "MAE is lower. Both are correct. Seasonal naive returns the exact integer "
            "count from the same hour last week, which on the many low-count hours is "
            "often exactly right and therefore proportionally perfect, while being "
            "further away in absolute terms. For staffing a cafe the absolute error is "
            "the decision-relevant one, so MAE is the gate and sMAPE is reported "
            "rather than optimised."
        ),
        "zones": results,
    }


def b2_segments(conn) -> dict:
    print("B2 segments — RFM with a bootstrap stability check")
    seg = segments.rfm(conn)
    curves = segments.response_curves(seg)
    print(f"    {len(seg.table)} customers, stability {seg.stability:.1%}")
    return {
        "task": "B2-segments",
        "generated_by": "scripts/run_phase_b.py",
        "generated_at": now_iso(),
        "method": (
            "RFM quintiles over the point-of-sale sample, assigned by a decision list "
            "so the rules read in order rather than as overlapping sets. Stability is "
            "the share of customers keeping their segment across 25 bootstrap "
            "resamples."
        ),
        "as_of": seg.as_of,
        "customers": int(len(seg.table)),
        "bootstrap_stability": seg.stability,
        "segments": json.loads(seg.summary.to_json(orient="records")),
        "response_curves": json.loads(curves.to_json(orient="records")),
        "curves_are_assumed": True,
        "note_on_curves": (
            "The response ceilings and saturation rates are structural assumptions, "
            "not fitted values: no promotion has run, so there is nothing to fit them "
            "to. Phase D's measured lift replaces them."
        ),
    }


def b3_allocator(conn) -> dict:
    print("B3 allocator — channel x daypart on a concave simplex")
    rows = conn.execute(
        "SELECT CASE "
        "WHEN CAST(substr(ts_local,12,2) AS INTEGER) >= 6 AND CAST(substr(ts_local,12,2) AS INTEGER) < 11 THEN 'morning' "
        "WHEN CAST(substr(ts_local,12,2) AS INTEGER) >= 11 AND CAST(substr(ts_local,12,2) AS INTEGER) < 17 THEN 'midday' "
        "WHEN CAST(substr(ts_local,12,2) AS INTEGER) >= 17 THEN 'evening' ELSE 'closed' END AS dp, "
        "SUM(footfall) n FROM footfall_hourly "
        "WHERE substr(ts_local,1,10) >= date((SELECT MAX(substr(ts_local,1,10)) FROM footfall_hourly), '-90 day') "
        "GROUP BY dp"
    ).fetchall()
    demand = {r["dp"]: r["n"] for r in rows if r["dp"] != "closed"}

    cells = allocator.build_cells(demand)
    budgets = [2000, 4000, 6000, 8000, 12000, 16000, 24000, 32000]
    plans = {}
    for b in budgets:
        a = allocator.allocate(cells, b)
        plans[str(b)] = {
            "total_response": a.total_response,
            "marginal_spread": a.marginal_spread,
            "sums_to_budget": abs(sum(c.spend for c in a.cells) - b) < 1e-6,
            "by_channel": {k: round(v, 2) for k, v in a.by_channel().items()},
            "by_daypart": {k: round(v, 2) for k, v in a.by_daypart().items()},
        }
    headline = allocator.allocate(cells, 12000)
    print(
        f"    12,000 AED -> {headline.total_response:,.0f} visits, "
        f"KKT spread {headline.marginal_spread:.2e}"
    )

    return {
        "task": "B3-allocator",
        "generated_by": "scripts/run_phase_b.py",
        "generated_at": now_iso(),
        "method": (
            "Fifteen cells — five channels by three dayparts — each with a saturating "
            "response a(1-exp(-bx)). The objective is concave, so greedy marginal "
            "allocation reaches the exact optimum and the KKT condition (equal "
            "marginal return across funded cells) is checkable."
        ),
        "daypart_demand_90d": demand,
        "cells": [
            {"channel": c.channel, "daypart": c.daypart, "ceiling": c.ceiling, "rate": c.rate}
            for c in cells
        ],
        "sweep": allocator.sweep(cells, budgets),
        "plans": plans,
        "parameters_are_assumed": True,
        "note_on_parameters": (
            "Affinities and saturation rates are structural assumptions scaled by the "
            "forecast, not fitted elasticities. No promotion has run. Every response "
            "the allocator returns carries assumed=true, and an allocator presented as "
            "optimal on invented elasticities would be the most confident wrong thing "
            "in this application."
        ),
    }


def b1_forward(conn) -> dict:
    """Precompute the forward horizon so nothing fits at request time.

    Fitting four sites takes about ninety seconds. Doing that inside a request
    on a 512 MB free instance is a timeout at best; doing it lazily and caching
    means the FIRST visitor pays for it, which is the worst possible person to
    charge. So the horizon is computed here, written to docs/results/, and
    served as data.

    The cost is that the horizon is as fresh as the last build. That is exactly
    right for this application: the underlying series is seeded and only moves
    when a pipeline runs, which on the deployed instance is at build time.
    """
    print("B1 forward — precomputing the 56-day horizon for four sites")
    out = {}
    for zone in [z.code for z in load_brand().zones]:
        df = forward(conn, zone, HORIZON_DAYS)
        out[zone] = json.loads(df.to_json(orient="records", date_format="iso"))
        print(f"    {zone}  {len(out[zone])} hourly points")
    return {
        "task": "B1-forward",
        "generated_by": "scripts/run_phase_b.py",
        "generated_at": now_iso(),
        "horizon_days": HORIZON_DAYS,
        "note": (
            "Precomputed rather than fitted per request. Ninety seconds of model "
            "fitting inside a request would time out on a free instance, and doing it "
            "lazily would charge the first visitor for it."
        ),
        "forward": out,
    }


def b4_uplift(conn) -> dict:
    print("B4 uplift — synthetic control, CUPED, and a recovery check")
    df = pd.read_sql_query(
        "SELECT substr(ts_local,1,10) d, zone_code, SUM(footfall) f "
        "FROM footfall_hourly GROUP BY d, zone_code",
        conn,
    )
    daily = df.pivot(index="d", columns="zone_code", values="f").dropna().astype(float)

    window = ("2026-06-01", "2026-06-14")
    checks = []
    for injected in (0.30, 0.20, 0.10, 0.05, 0.0):
        r = uplift.recovery_check(daily, "DXB-MAR", *window, injected=injected)
        checks.append(r)
        mark = "ok" if r["within_5_points"] else "MISS"
        print(
            f"    [{mark}] injected {injected:+.0%} -> {r['recovered']:+.2%} "
            f"(error {r['error_points']:+.2f} pts)"
        )

    live = uplift.synthetic_control(daily, "DXB-MAR", *window)
    bias = uplift.placebo_in_time(daily, "DXB-MAR", *window)

    return {
        "task": "B4-uplift",
        "generated_by": "scripts/run_phase_b.py",
        "generated_at": now_iso(),
        "method": (
            "Synthetic control with non-negative weights summing to one, fitted on 56 "
            "pre-period days; CUPED variance reduction; a permutation placebo across "
            "donor sites for the p-value; and a placebo-in-time run for the estimator's "
            "own bias."
        ),
        "tolerance_points": RECOVERY_TOLERANCE * 100,
        "recovery": checks,
        "all_within_tolerance": all(c["within_5_points"] for c in checks),
        "worst_error_points": max(abs(c["error_points"]) for c in checks),
        "example_window": {
            "treated": live.treated_zone,
            "window": list(window),
            "weights": live.weights,
            "pre_rmse": live.pre_rmse,
            "lift_raw": live.lift_raw,
            "bias": round(bias, 4),
            "variance_reduction": live.variance_reduction,
            "placebo_p": live.placebo_p,
        },
        "note_on_bias": (
            "The estimator returns about -3.5% on a window where nothing happened, and "
            "that is not noise. The donor blend is dominated by Al Barsha, which is "
            "fully enclosed; Marina Walk is more than half outdoor seating. As the Gulf "
            "summer arrives Marina falls away from its own history while the enclosed "
            "donor does not, so the counterfactual drifts above the treated site for "
            "reasons unrelated to any promotion. With four sites and one of them "
            "uniquely weather-elastic, no convex blend of the others can match Marina's "
            "weather response: it is inside the donors' hull on level and outside it on "
            "elasticity. That is a real limitation of synthetic control on a small "
            "donor pool, so it is measured on a placebo window and subtracted, and both "
            "numbers are reported."
        ),
    }


def main() -> int:
    conn = connect()
    payloads = [
        b1_forecast(conn),
        b1_forward(conn),
        b2_segments(conn),
        b3_allocator(conn),
        b4_uplift(conn),
    ]
    for p in payloads:
        write(p["task"], p)

    forecast, _, _, _, lift = payloads
    ok = forecast["meets_target"] and lift["all_within_tolerance"]
    print()
    print(
        f"forecast win rate  {forecast['win_rate']:.0%}  (target {WIN_RATE_TARGET:.0%})  "
        f"{'PASS' if forecast['meets_target'] else 'FAIL'}"
    )
    print(
        f"uplift recovery    worst error {lift['worst_error_points']:.2f} pts  "
        f"(tolerance {RECOVERY_TOLERANCE * 100:.0f})  "
        f"{'PASS' if lift['all_within_tolerance'] else 'FAIL'}"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
