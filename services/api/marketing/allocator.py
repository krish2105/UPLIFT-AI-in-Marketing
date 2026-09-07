"""Budget across channel x daypart.

WHY FIFTEEN CELLS AND NOT FIVE
------------------------------
A café's promo budget is small, so a channel-only split has almost nothing to
say — three channels and a few thousand dirhams is a decision anyone can make in
their head. The interesting structure is that a channel's payback DEPENDS ON THE
HOUR: delivery-aggregator spend works at midday and is wasted at 07:00, near-store
OOH only reaches people already within walking distance, and SMS to a regular
lands best just before the evening peak. Five channels times three dayparts is a
fifteen-cell simplex with real shape.

THE MATHEMATICS
---------------
Each cell has a saturating response r_i(x) = a_i * (1 - exp(-b_i * x)). That is
concave, so the total is concave, so the constrained optimum is unique and a
greedy marginal allocation finds it exactly: repeatedly give the next unit of
budget to whichever cell has the highest derivative. No solver, no local optima,
and the KKT condition — equal marginal return across every cell receiving money —
is checkable, which is what tests/marketing/test_allocator.py does.

WHERE THE PARAMETERS COME FROM, AND WHAT THAT MEANS
---------------------------------------------------
`a` and `b` are STRUCTURAL ASSUMPTIONS scaled by the forecast, not fitted values.
No promotion has run, so there is nothing to fit them to. Every response the
allocator returns carries `assumed: true`, the UI says so, and Phase D's measured
lift is what replaces them. An allocator presented as optimal on invented
elasticities would be the most confident wrong thing in this application.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CHANNELS: tuple[str, ...] = ("instagram", "google", "aggregator", "near_store_ooh", "sms_crm")
DAYPARTS: tuple[str, ...] = ("morning", "midday", "evening")

CHANNEL_LABEL = {
    "instagram": "Instagram",
    "google": "Google",
    "aggregator": "Delivery aggregator",
    "near_store_ooh": "Near-store OOH",
    "sms_crm": "SMS / CRM",
}

#: Relative effectiveness per channel-daypart. The shape is the claim; the
#: numbers are assumptions. Aggregator spend collapses in the morning because
#: nobody orders delivery coffee at 07:00; OOH peaks in the morning because it
#: catches a commuter already on the street.
AFFINITY: dict[str, dict[str, float]] = {
    "instagram": {"morning": 0.45, "midday": 0.80, "evening": 1.00},
    "google": {"morning": 0.70, "midday": 0.85, "evening": 0.75},
    "aggregator": {"morning": 0.20, "midday": 1.00, "evening": 0.85},
    "near_store_ooh": {"morning": 1.00, "midday": 0.55, "evening": 0.70},
    "sms_crm": {"morning": 0.60, "midday": 0.45, "evening": 0.95},
}

#: How fast each channel saturates, per 1,000 AED. A larger number means the
#: channel runs out of new people sooner — SMS reaches a finite list.
SATURATION: dict[str, float] = {
    "instagram": 0.55,
    "google": 0.40,
    "aggregator": 0.60,
    "near_store_ooh": 0.85,
    "sms_crm": 1.30,
}


@dataclass(frozen=True)
class Cell:
    channel: str
    daypart: str
    ceiling: float  # a — maximum incremental visits this cell can buy
    rate: float  # b — saturation rate per 1,000 AED
    spend: float = 0.0

    def response(self, spend: float | None = None) -> float:
        x = self.spend if spend is None else spend
        return self.ceiling * (1 - np.exp(-self.rate * x / 1000))

    def marginal(self, spend: float | None = None) -> float:
        """d(response)/d(spend), per AED. What the greedy step ranks on."""
        x = self.spend if spend is None else spend
        return self.ceiling * self.rate / 1000 * np.exp(-self.rate * x / 1000)


@dataclass(frozen=True)
class Allocation:
    budget: float
    cells: list[Cell]
    total_response: float
    #: Max spread of marginal return across funded cells. At the optimum of a
    #: concave problem this is ~0 — the KKT condition, checkable.
    marginal_spread: float
    assumed: bool = True

    def by_channel(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for c in self.cells:
            out[c.channel] = out.get(c.channel, 0.0) + c.spend
        return out

    def by_daypart(self) -> dict[str, float]:
        out: dict[str, float] = {}
        for c in self.cells:
            out[c.daypart] = out.get(c.daypart, 0.0) + c.spend
        return out


def build_cells(daypart_demand: dict[str, float]) -> list[Cell]:
    """Ceilings scale with forecast demand in that daypart.

    This is the one place the forecast enters the allocator: a channel cannot
    buy visits from an hour that has no visitors to win, so the evening's higher
    forecast raises every evening cell's ceiling proportionally.
    """
    total = sum(daypart_demand.values()) or 1.0
    cells = []
    for ch in CHANNELS:
        for dp in DAYPARTS:
            share = daypart_demand.get(dp, 0.0) / total
            cells.append(
                Cell(
                    channel=ch,
                    daypart=dp,
                    ceiling=round(AFFINITY[ch][dp] * share * 900, 2),
                    rate=SATURATION[ch],
                )
            )
    return cells


def allocate(cells: list[Cell], budget: float, step: float = 25.0) -> Allocation:
    """Greedy marginal allocation. Exact for a concave objective.

    Each step goes to the cell with the highest derivative at its current spend.
    Because every response is concave the derivative falls as a cell is funded,
    so the process converges on equal marginal return — which is the optimum,
    not an approximation of it.
    """
    spend = {(c.channel, c.daypart): 0.0 for c in cells}
    lookup = {(c.channel, c.daypart): c for c in cells}
    remaining = budget

    while remaining > 1e-9:
        unit = min(step, remaining)
        best = max(spend, key=lambda k: lookup[k].marginal(spend[k]))
        spend[best] += unit
        remaining -= unit

    funded = [
        Cell(c.channel, c.daypart, c.ceiling, c.rate, round(spend[(c.channel, c.daypart)], 2))
        for c in cells
    ]
    active = [c for c in funded if c.spend > 0]
    marginals = [c.marginal() for c in active]
    return Allocation(
        budget=budget,
        cells=funded,
        total_response=round(sum(c.response() for c in funded), 2),
        marginal_spread=round(float(max(marginals) - min(marginals)) if marginals else 0.0, 8),
    )


def sweep(cells: list[Cell], budgets: list[float]) -> list[dict]:
    """Total response across a range of budgets — the diminishing-returns curve
    the Plan tab's slider moves along."""
    out = []
    for b in budgets:
        a = allocate(cells, b)
        out.append(
            {
                "budget": b,
                "response": a.total_response,
                "marginal_per_1000": round(a.total_response / b * 1000, 2) if b else 0.0,
            }
        )
    return out
