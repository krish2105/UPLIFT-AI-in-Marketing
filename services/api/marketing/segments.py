"""RFM segmentation over the point-of-sale sample.

WHY RFM AND NOT A CLUSTERING ALGORITHM
--------------------------------------
k-means on transaction features produces clusters that move every time the data
is refreshed and that nobody can act on. RFM produces segments a shift manager
can name — someone who came last week and spends well is a different problem
from someone who has not come in three months — and the boundaries are
quantiles, which are stable and explainable.

The stability is not asserted, it is measured: `bootstrap_stability()` resamples
customers with replacement and reports how often a customer lands in the same
segment. A segmentation that reshuffles under resampling is describing noise.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import numpy as np
import pandas as pd

SEED = 20260907

#: (name, predicate over the R/F/M scores 1-5). Order matters: the first match
#: wins, so the rules read as a decision list rather than as overlapping sets.
SEGMENTS: list[tuple[str, str]] = [
    ("Champions", "r >= 4 and f >= 4"),
    ("Loyal", "f >= 4"),
    ("Big spenders", "m >= 4 and r >= 3"),
    ("Promising", "r >= 4"),
    ("At risk", "r <= 2 and f >= 3"),
    ("Hibernating", "r <= 2"),
    ("Occasional", "True"),
]

DESCRIPTION: dict[str, str] = {
    "Champions": "Recent and frequent. The evening regulars the whole estate runs on.",
    "Loyal": "Frequent but not necessarily recent. Worth a reason to come back this week.",
    "Big spenders": "Larger baskets, moderate frequency. Respond to bundles, not discounts.",
    "Promising": "Came recently, has not built a habit yet. The cheapest group to convert.",
    "At risk": "Used to be frequent and has stopped. The most expensive group to lose.",
    "Hibernating": "Long gone. Reactivation spend here rarely pays back.",
    "Occasional": "Everyone else. Do not build a campaign around them.",
}


@dataclass(frozen=True)
class Segmentation:
    table: pd.DataFrame  # one row per customer
    summary: pd.DataFrame  # one row per segment
    stability: float  # mean same-segment rate under bootstrap
    as_of: str


def _score(series: pd.Series, ascending: bool) -> pd.Series:
    """Quintile score 1-5.

    Ranked before cutting, because raw quantiles collapse when a value repeats
    often — and in a café most customers have visited exactly once, so the
    frequency distribution is mostly ties.
    """
    ranked = series.rank(method="first", ascending=ascending)
    return pd.qcut(ranked, 5, labels=[1, 2, 3, 4, 5]).astype(int)


def _label(r: int, f: int, m: int) -> str:
    for name, rule in SEGMENTS:
        if eval(rule, {"__builtins__": {}}, {"r": r, "f": f, "m": m}):  # noqa: S307
            return name
    return "Occasional"


def rfm(conn: sqlite3.Connection) -> Segmentation:
    baskets = pd.read_sql_query(
        "SELECT customer_id, ts_local, amount_aed, zone_code, daypart FROM pos_baskets", conn
    )
    baskets["ts"] = pd.to_datetime(baskets["ts_local"])
    as_of = baskets["ts"].max()

    g = baskets.groupby("customer_id")
    table = pd.DataFrame(
        {
            "recency_days": (as_of - g["ts"].max()).dt.days,
            "frequency": g.size(),
            "monetary": g["amount_aed"].sum(),
            "avg_basket": g["amount_aed"].mean(),
            "home_zone": g["zone_code"].agg(lambda s: s.mode().iat[0]),
            "home_daypart": g["daypart"].agg(lambda s: s.mode().iat[0]),
        }
    ).reset_index()

    table["r"] = _score(table["recency_days"], ascending=False)
    table["f"] = _score(table["frequency"], ascending=True)
    table["m"] = _score(table["monetary"], ascending=True)
    table["segment"] = [_label(r, f, m) for r, f, m in zip(table.r, table.f, table.m, strict=True)]

    summary = (
        table.groupby("segment")
        .agg(
            customers=("customer_id", "size"),
            revenue=("monetary", "sum"),
            avg_basket=("avg_basket", "mean"),
            median_recency=("recency_days", "median"),
            median_frequency=("frequency", "median"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    summary["revenue_share"] = summary["revenue"] / summary["revenue"].sum()
    summary["customer_share"] = summary["customers"] / summary["customers"].sum()
    summary["description"] = summary["segment"].map(DESCRIPTION)

    return Segmentation(
        table=table,
        summary=summary,
        stability=bootstrap_stability(table),
        as_of=as_of.strftime("%Y-%m-%d"),
    )


def bootstrap_stability(table: pd.DataFrame, rounds: int = 25, seed: int = SEED) -> float:
    """How often a customer keeps its segment when the sample is resampled.

    The quantile cuts move with the sample, so a customer near a boundary can
    legitimately change segment. What would not be legitimate is most of them
    moving — that would mean the segments describe the sample rather than the
    customers.
    """
    rng = np.random.default_rng(seed)
    base = dict(zip(table["customer_id"], table["segment"], strict=True))
    agree: list[float] = []
    for _ in range(rounds):
        sample = table.sample(frac=1.0, replace=True, random_state=int(rng.integers(1 << 31)))
        sample = sample.drop_duplicates("customer_id").copy()
        sample["r"] = _score(sample["recency_days"], ascending=False)
        sample["f"] = _score(sample["frequency"], ascending=True)
        sample["m"] = _score(sample["monetary"], ascending=True)
        relabelled = [_label(r, f, m) for r, f, m in zip(sample.r, sample.f, sample.m, strict=True)]
        agree.append(
            float(
                np.mean(
                    [base[c] == s for c, s in zip(sample["customer_id"], relabelled, strict=True)]
                )
            )
        )
    return round(float(np.mean(agree)), 4)


def response_curves(seg: Segmentation) -> pd.DataFrame:
    """A saturating response per segment, for the allocator.

    Shape: lift = a * (1 - exp(-b * spend_per_customer)). `a` is the ceiling and
    is set from how responsive the segment has shown itself to be — recency and
    frequency are the observable proxies — and `b` is how fast it saturates.
    These are STRUCTURAL assumptions, not fitted values: no promotion has run
    yet, so there is nothing to fit them to. They are labelled assumed wherever
    they surface, and Phase D's measured lift is what replaces them.
    """
    rows = []
    for s in seg.summary.itertuples():
        ceiling = {
            "Champions": 0.10,
            "Loyal": 0.16,
            "Big spenders": 0.14,
            "Promising": 0.26,
            "At risk": 0.22,
            "Hibernating": 0.06,
            "Occasional": 0.09,
        }.get(s.segment, 0.10)
        rate = {
            "Champions": 0.9,
            "Loyal": 0.7,
            "Big spenders": 0.6,
            "Promising": 0.5,
            "At risk": 0.45,
            "Hibernating": 0.3,
            "Occasional": 0.5,
        }.get(s.segment, 0.6)
        rows.append(
            {
                "segment": s.segment,
                "customers": int(s.customers),
                "revenue_share": round(float(s.revenue_share), 4),
                "ceiling": ceiling,
                "saturation_rate": rate,
                "assumed": True,
            }
        )
    return pd.DataFrame(rows)
