"""Calendar pipeline tests.

The pipeline builds pure rows from a reference date, so these run without a
database and without a network, and they pin the two things most likely to go
quietly wrong: the Hijri conversion, and the confidence label that tells a
reader how much to trust a date.
"""

from __future__ import annotations

from datetime import date

import pytest

from pipeline.calendar import COLUMNS, _in_window, build


@pytest.fixture(scope="module")
def days() -> dict[str, dict]:
    rows = build(today=date(2026, 9, 7))
    return {r[0]: dict(zip(COLUMNS, r, strict=True)) for r in rows}


def test_the_2025_observances_are_reproduced(days):
    """Calibration against dates the UAE actually observed.

    The Umm al-Qura tabular calendar is not guaranteed to match a moon sighting,
    so agreement here is evidence rather than proof — but it is the evidence the
    report is allowed to cite, and a regression in the converter shows up here.
    """
    assert days["2025-03-30"]["holiday_name"] == "Eid al-Fitr"
    assert days["2025-06-05"]["holiday_name"] == "Arafah Day"
    assert days["2025-06-06"]["holiday_name"] == "Eid al-Adha"
    assert days["2025-03-01"]["ramadan_day"] == 1


def test_eid_al_fitr_2026_is_computed_and_marked_uncertain(days):
    """2026 is ahead of any sighting, so the date is calculated and says so."""
    eid = days["2026-03-20"]
    assert eid["holiday_name"] == "Eid al-Fitr"
    assert eid["holiday_kind"] == "islamic"
    assert eid["date_uncertainty_days"] == 1
    assert eid["confidence"] == "calculated"


def test_eid_al_fitr_runs_three_days_per_the_uae_rule(days):
    """u.ae states Eid al-Fitr as 1-3 Shawwal."""
    span = [
        d for d, r in days.items() if r["holiday_name"] == "Eid al-Fitr" and d.startswith("2026")
    ]
    assert len(span) == 3, f"expected three days of Eid al-Fitr in 2026, got {span}"


def test_gregorian_holidays_are_certain_and_islamic_ones_are_not(days):
    assert days["2026-01-01"]["holiday_name"] == "New Year's Day"
    assert days["2026-01-01"]["date_uncertainty_days"] == 0
    assert days["2026-01-01"]["confidence"] == "observed"
    assert days["2025-12-02"]["holiday_name"] == "UAE National Day"


def test_commemoration_day_is_absent_because_u_ae_does_not_list_it(days):
    """Widely repeated elsewhere, and not in the official list. The source wins."""
    names = {r["holiday_name"] for r in days.values() if r["holiday_name"]}
    assert not any("Commemoration" in n for n in names)


def test_ramadan_is_never_also_eid(days):
    """They are opposite demand events for a cafe: daytime trade collapses
    through Ramadan and Eid is a straightforward peak. Conflating them would
    average the two into nonsense."""
    for d, r in days.items():
        if r["is_ramadan"]:
            assert r["holiday_name"] != "Eid al-Fitr", f"{d} is both Ramadan and Eid"


def test_ramadan_runs_a_lunar_month(days):
    lengths: dict[int, int] = {}
    for r in days.values():
        if r["is_ramadan"]:
            year = int(r["date_local"][:4])
            lengths[year] = lengths.get(year, 0) + 1
    for year, n in lengths.items():
        # A Ramadan clipped by the window edge is legitimately short.
        if 2025 <= year <= 2026:
            assert 28 <= n <= 30, f"Ramadan {year} has {n} days"


def test_school_breaks_are_always_marked_approximate(days):
    """KHDA's calendar is not machine-readable, so these are approximate
    windows. A row that claimed otherwise would be the pipeline overstating
    what it knows."""
    for d, r in days.items():
        if r["is_school_break"]:
            assert r["school_break_confidence"] == "approximate", d


def test_a_certain_holiday_inside_an_approximate_window_stays_certain(days):
    """The bug this pair of columns exists to prevent: New Year's Day sits
    inside the winter-break window, and a single confidence column downgraded
    it to approximate — asserting less about a date than is actually known."""
    ny = days["2026-01-01"]
    assert ny["is_school_break"] == 1
    assert ny["school_break_confidence"] == "approximate"
    assert ny["confidence"] == "observed"
    assert ny["date_uncertainty_days"] == 0


def test_the_winter_break_window_wraps_the_year():
    """The only window that crosses 31 December, and the classic off-by-one."""
    assert _in_window(date(2025, 12, 20), (12, 15), (1, 2))
    assert _in_window(date(2026, 1, 1), (12, 15), (1, 2))
    assert not _in_window(date(2026, 1, 10), (12, 15), (1, 2))
    assert not _in_window(date(2025, 11, 30), (12, 15), (1, 2))


def test_the_uae_weekend_is_saturday_and_sunday(days):
    assert days["2026-09-05"]["is_weekend"] == 1  # Saturday
    assert days["2026-09-06"]["is_weekend"] == 1  # Sunday
    assert days["2026-09-07"]["is_weekend"] == 0  # Monday
