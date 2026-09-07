"""The UAE calendar: public holidays, Ramadan, and school breaks.

THREE KINDS OF DATE, AND THEY ARE NOT EQUALLY KNOWN
---------------------------------------------------
This pipeline produces one day-level table, but the rows in it carry very
different amounts of certainty, and flattening that difference would be the
easiest way for this project to lie quietly.

  GREGORIAN HOLIDAYS   1 January, 2-3 December. Fixed, known years ahead.
                       confidence = 'observed'.

  ISLAMIC HOLIDAYS     Eid al-Fitr, Arafah, Eid al-Adha, Islamic New Year,
                       the Prophet's birthday, and Ramadan itself. u.ae states
                       plainly that "Islamic holidays are determined according
                       to moon sighting", so no calculation is authoritative.
                       These are computed from the Umm al-Qura tabular calendar
                       and carry date_uncertainty_days = 1.
                       confidence = 'calculated'.

  SCHOOL BREAKS        KHDA's academic-calendar page 301-redirects to a host
                       whose certificate chain does not verify, the MoE site
                       does not publish the calendar in machine-readable form,
                       and the u.ae path for it 404s — all checked on
                       2026-09-07 and recorded in docs/datasets.md. So these
                       are APPROXIMATE windows, not term dates: the summer
                       exodus, the winter break and the spring break, which are
                       broad and stable enough that a week either way does not
                       change the demand signal they carry. These carry their
                       own school_break_confidence = 'approximate', kept in a
                       separate column so that a certain holiday falling inside
                       an approximate window is not downgraded by it.

The forecaster reads `confidence` and the API exposes it, so a reader can
always see which of these three a given day is.

WHY THE HOLIDAY RULE SET IS THE ONE u.ae PUBLISHES
--------------------------------------------------
Verified by fetching on 2026-09-07: Eid al-Fitr runs 1-3 Shawwal, Arafah is
9 Dhu al-Hijjah, Eid al-Adha is 10-12 Dhu al-Hijjah, Islamic New Year is
1 Muharram, the Prophet's birthday is 12 Rabi' al-Awwal, and National Day is
2-3 December. Commemoration Day is NOT in that list and is therefore not here
either, even though it is widely repeated elsewhere.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

from hijridate import Gregorian, Hijri  # noqa: E402

from pipeline.common import Result  # noqa: E402
from services.api.core.db import connect, upsert_many  # noqa: E402

CSV_OUT = ROOT / "data" / "raw" / "uae_calendar.csv"

HISTORY_DAYS = 760  # a little over 24 months back
HORIZON_DAYS = 400  # and 12 months forward

#: (name, hijri month, first day, length in days) per the u.ae rule set.
ISLAMIC_HOLIDAYS: list[tuple[str, int, int, int]] = [
    ("Islamic New Year", 1, 1, 1),
    ("Prophet Muhammad's birthday", 3, 12, 1),
    ("Eid al-Fitr", 10, 1, 3),
    ("Arafah Day", 12, 9, 1),
    ("Eid al-Adha", 12, 10, 3),
]

#: (name, month, day, length)
GREGORIAN_HOLIDAYS: list[tuple[str, int, int, int]] = [
    ("New Year's Day", 1, 1, 1),
    ("UAE National Day", 12, 2, 2),
]

#: Approximate school-break windows as (name, start month/day, end month/day).
#: The summer window is the one that matters most: Dubai's expat families leave
#: and the city's demand profile changes shape for two months. That effect is
#: large and slow, so a week of imprecision at either edge does not move it.
SCHOOL_BREAKS: list[tuple[str, tuple[int, int], tuple[int, int]]] = [
    ("Summer break", (7, 1), (8, 25)),
    ("Winter break", (12, 15), (1, 2)),
    ("Spring break", (3, 18), (4, 1)),
]

COLUMNS = (
    "date_local",
    "weekday",
    "is_weekend",
    "is_public_holiday",
    "holiday_name",
    "holiday_kind",
    "date_uncertainty_days",
    "is_ramadan",
    "ramadan_day",
    "is_school_break",
    "school_break_name",
    "confidence",
    "school_break_confidence",
)


def _islamic_dates(start: date, end: date) -> dict[date, tuple[str, int]]:
    """Map Gregorian date -> (holiday name, uncertainty days) across the window."""
    out: dict[date, tuple[str, int]] = {}
    # Walk Hijri years generously either side so a holiday near a boundary is
    # not clipped.
    h_start = Gregorian(start.year, start.month, start.day).to_hijri().year - 1
    h_end = Gregorian(end.year, end.month, end.day).to_hijri().year + 1
    for hy in range(h_start, h_end + 1):
        for name, hm, hd, length in ISLAMIC_HOLIDAYS:
            try:
                first = Hijri(hy, hm, hd).to_gregorian()
            except (ValueError, OverflowError):
                continue
            g = date(first.year, first.month, first.day)
            for i in range(length):
                out[g + timedelta(days=i)] = (name, 1)
    return out


def _ramadan_days(start: date, end: date) -> dict[date, int]:
    """Map Gregorian date -> day of Ramadan (1-30).

    Ramadan is kept separate from Eid because they are opposite demand events
    for a cafe: daytime trade collapses through the month and the hours after
    iftar carry it, then Eid is a straightforward peak. A single "holiday" flag
    would average those into nonsense.
    """
    out: dict[date, int] = {}
    h_start = Gregorian(start.year, start.month, start.day).to_hijri().year - 1
    h_end = Gregorian(end.year, end.month, end.day).to_hijri().year + 1
    for hy in range(h_start, h_end + 1):
        for day in range(1, 31):
            try:
                g = Hijri(hy, 9, day).to_gregorian()
            except (ValueError, OverflowError):
                continue
            out[date(g.year, g.month, g.day)] = day
    return out


def _in_window(d: date, start: tuple[int, int], end: tuple[int, int]) -> bool:
    """Month/day window membership, handling the winter break's year wrap."""
    s = (start[0], start[1])
    e = (end[0], end[1])
    cur = (d.month, d.day)
    return s <= cur or cur <= e if s > e else s <= cur <= e


def build(today: date | None = None) -> list[tuple]:
    today = today or date.today()
    start = today - timedelta(days=HISTORY_DAYS)
    end = today + timedelta(days=HORIZON_DAYS)

    islamic = _islamic_dates(start, end)
    ramadan = _ramadan_days(start, end)
    gregorian: dict[date, str] = {}
    for year in range(start.year, end.year + 1):
        for name, m, dd, length in GREGORIAN_HOLIDAYS:
            first = date(year, m, dd)
            for i in range(length):
                gregorian[first + timedelta(days=i)] = name

    rows: list[tuple] = []
    d = start
    while d <= end:
        holiday_name = holiday_kind = None
        uncertainty = 0
        confidence = "observed"

        if d in gregorian:
            holiday_name, holiday_kind = gregorian[d], "gregorian"
        elif d in islamic:
            holiday_name, uncertainty = islamic[d]
            holiday_kind = "islamic"
            confidence = "calculated"

        # `confidence` describes the HOLIDAY determination and nothing else.
        # The school-break window has its own column, because a fixed Gregorian
        # holiday that happens to fall inside an approximate window is still a
        # fixed date — collapsing the two made New Year's Day read as uncertain.
        break_name = next((n for n, s, e in SCHOOL_BREAKS if _in_window(d, s, e)), None)

        rows.append(
            (
                d.isoformat(),
                d.weekday(),
                int(d.weekday() >= 5),  # UAE weekend: Saturday and Sunday
                int(holiday_name is not None),
                holiday_name,
                holiday_kind,
                uncertainty,
                int(d in ramadan),
                ramadan.get(d),
                int(break_name is not None),
                break_name,
                confidence,
                "approximate" if break_name else None,
            )
        )
        d += timedelta(days=1)
    return rows


def run(today: date | None = None) -> dict:
    rows = build(today)
    conn = connect()
    written = upsert_many(conn, "calendar_days", COLUMNS, rows)

    CSV_OUT.parent.mkdir(parents=True, exist_ok=True)
    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        w.writerows(rows)
    return {"written": written, "csv": str(CSV_OUT.relative_to(ROOT))}


def verify() -> int:
    conn = connect()
    r = Result(
        task="A5-calendar", dataset="calendar_days", generated_by="pipeline/calendar.py --verify"
    )

    total = conn.execute("SELECT COUNT(*) FROM calendar_days").fetchone()[0]
    span = conn.execute("SELECT MIN(date_local) a, MAX(date_local) b FROM calendar_days").fetchone()
    holidays = {
        row["holiday_name"]: row["n"]
        for row in conn.execute(
            "SELECT holiday_name, COUNT(*) n FROM calendar_days "
            "WHERE is_public_holiday=1 GROUP BY holiday_name"
        )
    }
    r.stats = {
        "rows": total,
        "span": [span["a"], span["b"]],
        "holiday_days_by_name": holidays,
        "confidence_mix": {
            row["confidence"]: row["n"]
            for row in conn.execute(
                "SELECT confidence, COUNT(*) n FROM calendar_days GROUP BY confidence"
            )
        },
        "ramadan_days": conn.execute(
            "SELECT COUNT(*) FROM calendar_days WHERE is_ramadan=1"
        ).fetchone()[0],
    }

    r.check(
        "covers at least 24 months of history plus a year ahead", total >= 1100, f"{total} days"
    )
    r.check("no missing days in the range", _no_gaps(conn), "consecutive dates")

    # Calibration against observances this project can state. The Umm al-Qura
    # tabular calendar is not guaranteed to agree with a moon sighting, so
    # agreeing on three known dates is evidence, not proof — and it is the
    # evidence the report is allowed to cite.
    known = {
        "2025-03-01": "Ramadan began in the UAE",
        "2025-03-30": "Eid al-Fitr",
        "2025-06-05": "Arafah Day",
        "2025-06-06": "Eid al-Adha",
    }
    matched = {}
    for iso in known:
        row = conn.execute(
            "SELECT holiday_name, is_ramadan, ramadan_day FROM calendar_days WHERE date_local=?",
            (iso,),
        ).fetchone()
        if row is None:
            matched[iso] = "outside the loaded range"
            continue
        matched[iso] = row["holiday_name"] or (
            f"Ramadan day {row['ramadan_day']}" if row["is_ramadan"] else None
        )
    r.stats["calibration_2025"] = {
        k: {"expected": known[k], "computed": v} for k, v in matched.items()
    }
    r.check(
        "computed dates agree with the 2025 UAE observances",
        matched.get("2025-03-30") == "Eid al-Fitr"
        and matched.get("2025-06-06") == "Eid al-Adha"
        and matched.get("2025-06-05") == "Arafah Day"
        and matched.get("2025-03-01") == "Ramadan day 1",
        str(matched),
    )

    r.check(
        "every Islamic holiday carries its moon-sighting uncertainty",
        conn.execute(
            "SELECT COUNT(*) FROM calendar_days WHERE holiday_kind='islamic' AND date_uncertainty_days=0"
        ).fetchone()[0]
        == 0,
        "date_uncertainty_days = 1 on all Islamic rows",
    )
    r.check(
        "Ramadan is flagged separately from Eid",
        conn.execute(
            "SELECT COUNT(*) FROM calendar_days WHERE is_ramadan=1 AND holiday_name='Eid al-Fitr'"
        ).fetchone()[0]
        == 0,
        "no day is both",
    )
    r.check(
        "every school break is labelled approximate",
        conn.execute(
            "SELECT COUNT(*) FROM calendar_days "
            "WHERE is_school_break=1 AND school_break_confidence!='approximate'"
        ).fetchone()[0]
        == 0,
        "KHDA's calendar is not machine-readable; see docs/datasets.md",
    )
    r.check(
        "a certain holiday inside an approximate window stays certain",
        conn.execute(
            "SELECT confidence FROM calendar_days WHERE date_local='2026-01-01'"
        ).fetchone()[0]
        == "observed",
        "New Year's Day sits inside the winter break and is still a fixed date",
    )
    return r.report()


def _no_gaps(conn) -> bool:
    dates = [
        date.fromisoformat(r[0])
        for r in conn.execute("SELECT date_local FROM calendar_days ORDER BY date_local")
    ]
    return all((dates[i] - dates[i - 1]).days == 1 for i in range(1, len(dates)))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    if not args.verify:
        meta = run()
        print(f"calendar: {meta['written']:,} days written, csv at {meta['csv']}")
        return 0
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
