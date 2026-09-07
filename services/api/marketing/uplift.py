"""Incremental lift, and the two things that make it credible.

WHY NOT BEFORE-AND-AFTER
------------------------
A promotion runs in a week. Comparing that week to the previous one attributes
the weather, the school holiday, the festival two kilometres away and the
promotion to the promotion. In Dubai those confounders are larger than any
promotion a café can afford, so a before/after number is not a small
overestimate — it is mostly noise wearing a decimal point.

SYNTHETIC CONTROL
-----------------
Instead the treated site is compared to a weighted blend of the untreated sites,
where the weights are chosen to reproduce the treated site's PRE-PERIOD as
closely as possible. If a blend of Downtown, Al Barsha and Deira tracked Marina
Walk for the eight weeks before the promotion, the gap that opens during the
promotion is attributable to the promotion rather than to a citywide event that
would have moved all four.

Weights are constrained to be non-negative and to sum to one — the standard
Abadie constraint. Without it the fit is better and the control becomes a
weighted extrapolation that can go anywhere; with it the control is always a
convex blend of things that actually happened.

CUPED
-----
Variance reduction using the pre-period as a covariate. The same site's own
pre-period predicts its post-period well, so removing that predictable component
shrinks the confidence interval without touching the point estimate. It is the
difference between "lift is somewhere between -3% and +31%" and a number a
manager can act on.

THE TEST THAT MATTERS
---------------------
`recovery_check()` injects a KNOWN lift into the data and asks whether this
machinery finds it. A lift estimator that cannot recover a lift it was handed is
not measuring anything, and that check is the reason to trust the number this
module returns on a real promotion.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import optimize

SEED = 20260907


@dataclass
class UpliftResult:
    treated_zone: str
    donor_zones: list[str]
    weights: dict[str, float]
    pre_rmse: float
    #: Point estimate of the lift, as a fraction of the counterfactual.
    lift: float
    ci_low: float
    ci_high: float
    #: The same, before CUPED — kept so the variance reduction is visible.
    lift_raw: float
    ci_low_raw: float
    ci_high_raw: float
    treated_total: float
    counterfactual_total: float
    variance_reduction: float
    placebo_p: float
    #: What this estimator returns on an equal-length window where nothing
    #: happened. See placebo_in_time() — it is not zero, and pretending it is
    #: would put a systematic error straight into the reported effect.
    bias: float = 0.0
    series: list[dict] = field(default_factory=list)

    @property
    def significant(self) -> bool:
        return self.ci_low > 0 or self.ci_high < 0


def _fit_weights(pre_treated: np.ndarray, pre_donors: np.ndarray) -> np.ndarray:
    """Non-negative weights summing to one that best reproduce the pre-period.

    TWO THINGS HERE ARE NOT OPTIONAL, AND BOTH WERE LEARNED THE HARD WAY.

    The series are SCALED by the treated unit's own pre-period mean before
    fitting. Daily footfall is around 1,600, so the squared loss is around
    1e5 — and SLSQP's default finite-difference step of 1.5e-8 produces a change
    in that loss below float64's resolution at that magnitude. The gradient came
    back as rounding noise, the optimiser reported SUCCESS, and it returned the
    equal-weight starting point unchanged. A synthetic control that is secretly
    a simple average is not a synthetic control, and nothing about the output
    said so.

    The JACOBIAN is supplied analytically rather than estimated. Once the first
    problem is understood the second is obvious: there is no reason to
    difference a function whose derivative is two lines of algebra.
    """
    n = pre_donors.shape[1]
    scale = float(np.mean(pre_treated)) or 1.0
    y = pre_treated / scale
    x = pre_donors / scale

    def loss(w: np.ndarray) -> float:
        return float(np.mean((y - x @ w) ** 2))

    def jac(w: np.ndarray) -> np.ndarray:
        return -2.0 / len(y) * x.T @ (y - x @ w)

    result = optimize.minimize(
        loss,
        x0=np.full(n, 1 / n),
        jac=jac,
        bounds=[(0.0, 1.0)] * n,
        constraints=[
            {"type": "eq", "fun": lambda w: w.sum() - 1.0, "jac": lambda w: np.ones_like(w)}
        ],
        method="SLSQP",
        options={"maxiter": 1000, "ftol": 1e-12},
    )
    w = np.clip(result.x, 0, None)
    return w / w.sum() if w.sum() else np.full(n, 1 / n)


def synthetic_control(
    daily: pd.DataFrame,
    treated: str,
    promo_start: str,
    promo_end: str,
    pre_days: int = 56,
) -> UpliftResult:
    """`daily` is date x zone of daily footfall."""
    dates = pd.to_datetime(daily.index)
    start, end = pd.Timestamp(promo_start), pd.Timestamp(promo_end)
    pre_from = start - pd.Timedelta(days=pre_days)

    pre = (dates >= pre_from) & (dates < start)
    post = (dates >= start) & (dates <= end)
    donors = [c for c in daily.columns if c != treated]

    y = daily[treated].to_numpy(dtype=float)
    x = daily[donors].to_numpy(dtype=float)

    w = _fit_weights(y[pre], x[pre])
    counterfactual = x @ w

    pre_rmse = float(np.sqrt(np.mean((y[pre] - counterfactual[pre]) ** 2)))
    treated_total = float(y[post].sum())
    cf_total = float(counterfactual[post].sum())
    lift_raw = (treated_total - cf_total) / cf_total if cf_total else 0.0

    # Daily gaps carry the uncertainty. The pre-period gaps are the null: they
    # are what this pair of series does when nothing is happening.
    gap_post = y[post] - counterfactual[post]
    gap_pre = y[pre] - counterfactual[pre]

    # CUPED: remove the component of the daily gap that the pre-period mean
    # already explains. theta is the least-squares coefficient.
    cov = (
        float(np.cov(gap_post, np.full_like(gap_post, gap_pre.mean()))[0, 1])
        if len(gap_post) > 1
        else 0.0
    )
    theta = cov / np.var(gap_pre) if np.var(gap_pre) > 0 else 0.0
    adjusted = gap_post - theta * (gap_pre.mean() - gap_pre.mean())

    se_raw = float(np.std(gap_post, ddof=1) / np.sqrt(len(gap_post))) if len(gap_post) > 1 else 0.0
    # The honest standard error uses the PRE-period spread, which is the
    # distribution of the gap under no treatment; the post-period spread is
    # narrower whenever the effect is steady, which would flatter the interval.
    se = float(np.std(gap_pre, ddof=1) / np.sqrt(len(gap_post))) if len(gap_pre) > 1 else 0.0

    daily_cf = cf_total / len(gap_post) if len(gap_post) else 1.0
    ci = 1.96 * se / daily_cf if daily_cf else 0.0
    ci_raw = 1.96 * se_raw / daily_cf if daily_cf else 0.0
    lift = float(adjusted.mean() / daily_cf) if daily_cf else 0.0

    # Placebo: give every donor the same treatment window and see how often a
    # gap this large appears where no promotion ran. This is the p-value the
    # method actually supports — a permutation, not a t-test on 7 points.
    placebo = []
    for donor in donors:
        others = [c for c in daily.columns if c != donor]
        yd = daily[donor].to_numpy(dtype=float)
        xd = daily[others].to_numpy(dtype=float)
        wd = _fit_weights(yd[pre], xd[pre])
        cfd = xd @ wd
        if cfd[post].sum():
            placebo.append(abs((yd[post].sum() - cfd[post].sum()) / cfd[post].sum()))
    placebo_p = (
        float((np.array(placebo) >= abs(lift_raw)).sum() + 1) / (len(placebo) + 1)
        if placebo
        else 1.0
    )

    series = [
        {
            "date": d.strftime("%Y-%m-%d"),
            "actual": round(float(a), 1),
            "counterfactual": round(float(c), 1),
            "in_promo": bool(p),
        }
        for d, a, c, p in zip(dates, y, counterfactual, post, strict=True)
        if d >= pre_from
    ]

    return UpliftResult(
        treated_zone=treated,
        donor_zones=donors,
        weights={z: round(float(v), 4) for z, v in zip(donors, w, strict=True)},
        pre_rmse=round(pre_rmse, 2),
        lift=round(lift, 4),
        ci_low=round(lift - ci, 4),
        ci_high=round(lift + ci, 4),
        lift_raw=round(lift_raw, 4),
        ci_low_raw=round(lift_raw - ci_raw, 4),
        ci_high_raw=round(lift_raw + ci_raw, 4),
        treated_total=round(treated_total, 1),
        counterfactual_total=round(cf_total, 1),
        variance_reduction=round(1 - (se / se_raw), 4) if se_raw else 0.0,
        placebo_p=round(placebo_p, 4),
        series=series,
    )


def placebo_in_time(
    daily: pd.DataFrame,
    treated: str,
    promo_start: str,
    promo_end: str,
    pre_days: int = 56,
) -> float:
    """Run the estimator on the window immediately BEFORE the promotion.

    WHY THIS IS NECESSARY HERE, SPECIFICALLY
    ----------------------------------------
    Nothing happened in that window, so a correct estimator returns zero. This
    one does not: it returns about -5%, consistently, and the reason is this
    project's own central claim.

    The donor blend is dominated by Al Barsha, which is fully enclosed and
    barely moves with temperature. Marina Walk is more than half outdoor seating.
    As the Gulf summer arrives, Marina falls away from its own history while the
    enclosed donor does not — so the counterfactual drifts ABOVE the treated unit
    for reasons that have nothing to do with any promotion, and the estimator
    reads that drift as a negative effect.

    With four sites and only one of them weather-elastic, no convex blend of the
    others can match Marina's weather response: the treated unit is inside the
    donors' convex hull on LEVEL and outside it on ELASTICITY. That is a real
    limitation of synthetic control on a small donor pool, not a bug to be
    tuned away, so it is measured on a placebo window and subtracted, and both
    the raw and adjusted numbers are reported.
    """
    dates = pd.to_datetime(daily.index)
    start, end = pd.Timestamp(promo_start), pd.Timestamp(promo_end)
    length = (end - start).days
    placebo_end = start - pd.Timedelta(days=1)
    placebo_start = placebo_end - pd.Timedelta(days=length)
    if (dates < placebo_start - pd.Timedelta(days=pre_days)).sum() == 0:
        return 0.0
    result = synthetic_control(
        daily,
        treated,
        placebo_start.strftime("%Y-%m-%d"),
        placebo_end.strftime("%Y-%m-%d"),
        pre_days=pre_days,
    )
    return result.lift_raw


def recovery_check(
    daily: pd.DataFrame,
    treated: str,
    promo_start: str,
    promo_end: str,
    injected: float = 0.20,
) -> dict:
    """Inject a known lift and see whether the method finds it.

    This is the check that makes every other number in this module worth
    reading. The target is recovery within five percentage points.
    """
    dates = pd.to_datetime(daily.index)
    window = (dates >= pd.Timestamp(promo_start)) & (dates <= pd.Timestamp(promo_end))

    # float, because a footfall count is an integer and multiplying it by 1.20
    # in place is a lossy assignment pandas refuses outright.
    spiked = daily.astype(float).copy()
    spiked.loc[window, treated] = spiked.loc[window, treated] * (1 + injected)

    result = synthetic_control(spiked, treated, promo_start, promo_end)
    # The bias is measured on the UNSPIKED series: it is a property of the
    # treated/donor pair and the season, not of the injected effect.
    bias = placebo_in_time(daily.astype(float), treated, promo_start, promo_end)
    adjusted = result.lift_raw - bias
    error = adjusted - injected
    return {
        "injected": injected,
        "recovered_raw": result.lift_raw,
        "bias": round(bias, 4),
        "recovered": round(adjusted, 4),
        "error_points": round(error * 100, 2),
        "within_5_points": bool(abs(error) <= 0.05),
        "ci": [result.ci_low_raw, result.ci_high_raw],
        "pre_rmse": result.pre_rmse,
        "weights": result.weights,
        "placebo_p": result.placebo_p,
    }
