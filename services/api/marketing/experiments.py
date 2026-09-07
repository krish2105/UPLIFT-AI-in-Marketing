"""Designing a promotion so its effect can be measured at all.

WHY THIS TAB EXISTS
-------------------
Most promotions are unmeasurable by construction: they run everywhere at once,
so there is nothing to compare against, and the analysis is chosen after the
result is seen. Both are decided BEFORE the promotion, or not at all.

Minimum detectable effect is the honest gate. Given the site's own daily noise
and the length of the window, there is a smallest lift the method could
distinguish from nothing — and if the promotion is not expected to clear it, the
promotion should either run longer, run on a noisier-free site, or not be
measured at all. Running it and reporting whatever number comes out is the thing
this page exists to prevent.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import numpy as np
import pandas as pd

#: Two-sided test at 95% with 80% power. z(0.975) + z(0.80).
Z_ALPHA = 1.959964
Z_POWER = 0.841621


@dataclass(frozen=True)
class Design:
    zone: str
    days: int
    daily_mean: float
    daily_sd: float
    cv: float
    mde: float
    pre_days: int
    donors: list[str]

    @property
    def mde_pct(self) -> float:
        return self.mde * 100


def daily_matrix(conn: sqlite3.Connection) -> pd.DataFrame:
    df = pd.read_sql_query(
        "SELECT substr(ts_local,1,10) d, zone_code, SUM(footfall) f "
        "FROM footfall_hourly GROUP BY d, zone_code",
        conn,
    )
    return df.pivot(index="d", columns="zone_code", values="f").dropna().astype(float)


def minimum_detectable_effect(
    daily: pd.DataFrame, zone: str, days: int, pre_days: int = 56
) -> Design:
    """The smallest lift this window could distinguish from noise.

    The noise that matters is not the site's own variability — it is the
    variability of the GAP between the site and its synthetic control, because
    that is what the estimator reads. A site can be volatile and still cheap to
    measure if its control is volatile in the same way.
    """
    from services.api.marketing.uplift import _fit_weights

    donors = [c for c in daily.columns if c != zone]
    tail = daily.tail(pre_days)
    w = _fit_weights(tail[zone].to_numpy(), tail[donors].to_numpy())
    gap = tail[zone].to_numpy() - tail[donors].to_numpy() @ w

    mean = float(tail[zone].mean())
    sd = float(np.std(gap, ddof=1))
    # Standard MDE for a mean over `days` observations.
    mde = (Z_ALPHA + Z_POWER) * sd / np.sqrt(days) / mean if mean else 0.0

    return Design(
        zone=zone,
        days=days,
        daily_mean=round(mean, 1),
        daily_sd=round(sd, 1),
        cv=round(sd / mean, 4) if mean else 0.0,
        mde=round(float(mde), 4),
        pre_days=pre_days,
        donors=donors,
    )


def sweep(
    conn: sqlite3.Connection, zone: str, lengths: tuple[int, ...] = (3, 7, 14, 21, 28, 42, 56)
) -> list[dict]:
    daily = daily_matrix(conn)
    return [
        {
            "days": d,
            "mde": minimum_detectable_effect(daily, zone, d).mde,
            "mde_pct": round(minimum_detectable_effect(daily, zone, d).mde * 100, 2),
        }
        for d in lengths
    ]


def all_zones(conn: sqlite3.Connection, days: int = 14) -> list[Design]:
    daily = daily_matrix(conn)
    return [minimum_detectable_effect(daily, z, days) for z in daily.columns]
