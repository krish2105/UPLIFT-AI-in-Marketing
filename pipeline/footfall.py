"""Generated hourly footfall for the four SIDRA sites, and a POS sample.

THIS DATA IS INVENTED, AND THAT IS THE POINT OF SAYING SO LOUDLY
---------------------------------------------------------------
No public hourly footfall series exists for any Dubai cafe. RAQIB/MASAR, the
sibling operations project, faced the same gap and solved it the same way — a
seeded generator whose output is labelled at the type level — and this
reimplements that pattern rather than importing it: multiplicative decomposition
of shape, rhythm, trend and shocks, with lognormal noise.

What is NOT invented is the evaluation. Phase B scores the forecaster against a
seasonal-naive baseline on held-out data, and a model that cannot beat "same
hour last week" is not used. A forecast that cannot outperform that is worse
than no forecast, because it looks like knowledge.

WHY THE ELASTICITIES ARE NOT WRITTEN DOWN HERE
----------------------------------------------
The interesting claim in this project is that the four sites respond
DIFFERENTLY to the same weather, and that this is why demand is forecast per
zone. It would be circular to hardcode "Marina is steeper" in the generator and
then assert it in a test.

So the weather elasticity is DERIVED from `outdoor_seats / total_seats` in
data/brand/sidra.yaml. Marina Walk is 46 of 86 seats outdoors and Al Barsha is
0 of 68, so the difference emerges from the brand definition rather than from a
constant in this file. Change the seat counts and the elasticity follows;
tests/data/test_footfall.py asserts the emergent ordering, not the input.

THE COMPONENTS
--------------
  daypart shape    bimodal, from the brand kit's per-zone profile: a commuter
                   peak before 11:00 and a longer evening peak after 17:00,
                   with Deira waking earliest and Marina latest.
  weekly rhythm    Thursday and Friday evenings are the week's peak; the UAE
                   weekend is Saturday and Sunday.
  trend            a slow drift, so the series is not stationary and the
                   baseline has something to be wrong about.
  Ramadan          daytime trade collapses and the hours after iftar surge.
                   Not a "holiday multiplier" — the SHAPE of the day inverts.
  weather          apparent temperature against the zone's outdoor share.
  events           scale weight decayed by distance from the site.
  noise            lognormal, seeded, so two runs are byte-identical.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

from pipeline.common import Result  # noqa: E402
from services.api.brand import load_brand  # noqa: E402
from services.api.core.db import connect, upsert_many  # noqa: E402
from services.api.simulated import BasketRecord, FootfallRecord  # noqa: E402

SEED = 20260907
CSV_OUT = ROOT / "data" / "pos_sample.csv"

#: Visitors per hour at each site's own peak, before any modifier. Scaled from
#: seat count, because a 32-seat Deira counter cannot turn over like an 86-seat
#: Marina terrace.
PEAK_PER_SEAT = 1.85

#: Hour at which each zone's morning and evening lobes are centred, and how
#: broad each lobe is. Deira wakes on the market trade; Marina lives after dark.
DAYPART_PROFILE: dict[str, tuple[float, float, float, float, float]] = {
    # zone: (morning centre, morning width, evening centre, evening width, morning share)
    "DXB-DEI": (7.5, 2.1, 18.5, 2.6, 0.62),
    "DXB-DTN": (9.0, 2.4, 19.5, 3.0, 0.44),
    "DXB-MOE": (10.5, 2.6, 19.0, 3.2, 0.38),
    "DXB-MAR": (8.5, 2.0, 21.0, 3.1, 0.28),
}

#: Monday=0. Thursday and Friday evenings carry the week in the UAE.
WEEKDAY_FACTOR = np.array([0.92, 0.94, 0.97, 1.08, 1.18, 1.14, 1.02])

#: How far an event's pull reaches. Beyond about 8 km a Dubai event does not
#: move a neighbourhood cafe.
EVENT_DECAY_KM = 6.0

#: Comfortable apparent temperature for sitting outside. Above this an outdoor
#: terrace empties; below it, it fills.
COMFORT_APPARENT_C = 30.0

#: The three cells the media allocator optimises over. The boundaries follow
#: SIDRA's actual trading hours rather than a tidy 8/12/17 split: Deira opens at
#: 06:00 on the market trade, and Marina Walk serves until 01:00. An earlier
#: version started the morning at 07:00 and ended the evening at midnight, which
#: labelled 155 real Deira baskets "closed" and threw away Marina's late hour.
DAYPARTS = (("morning", 6, 11), ("midday", 11, 17), ("evening", 17, 24))

#: Hours after midnight that still belong to the previous evening's trade.
LATE_EVENING_UNTIL = 2


def daypart_of(hour: int) -> str:
    if hour < LATE_EVENING_UNTIL:
        return "evening"
    for name, lo, hi in DAYPARTS:
        if lo <= hour < hi:
            return name
    return "closed"


def opening_mask(opens: str, closes: str) -> np.ndarray:
    """1 for each hour the site is trading, 0 otherwise.

    Marina Walk closes at 01:00, so the window wraps midnight. Without this the
    Gaussian daypart lobes leak a thin tail of trade into hours the shutters are
    down — which showed up as point-of-sale baskets at 04:00.
    """
    o = int(opens[:2])
    c = int(closes[:2])
    h = np.arange(24)
    return ((h >= o) | (h < c)).astype(float) if c <= o else ((h >= o) & (h < c)).astype(float)


def _lobe(hours: np.ndarray, centre: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((hours - centre) / width) ** 2)


def shape_for(zone_code: str, opens: str | None = None, closes: str | None = None) -> np.ndarray:
    """The zone's 24-hour profile, normalised so its peak is 1.0.

    Masked by the site's own opening hours when they are given: a Gaussian lobe
    has no natural zero, so without the mask a closed cafe still trades a
    trickle at 04:00.
    """
    mc, mw, ec, ew, share = DAYPART_PROFILE[zone_code]
    h = np.arange(24, dtype=float)
    curve = share * _lobe(h, mc, mw) + (1 - share) * _lobe(h, ec, ew)
    if opens and closes:
        curve = curve * opening_mask(opens, closes)
    return curve / curve.max()


def weather_factor(
    apparent_c: np.ndarray, precip_mm: np.ndarray, outdoor_share: float, hours: np.ndarray
) -> np.ndarray:
    """How weather moves this zone, given how much of it is outdoors.

    An enclosed mall site has outdoor_share 0 and is left almost untouched; a
    terrace is pushed hard both ways. The effect is applied only in the hours a
    terrace is actually used, which is why a 41C afternoon and a 41C 03:00 are
    not the same event.
    """
    excess = np.clip(apparent_c - COMFORT_APPARENT_C, 0, None)
    relief = np.clip(COMFORT_APPARENT_C - apparent_c, 0, 10)
    outdoor_hours = ((hours >= 16) | (hours <= 11)).astype(float)

    heat_penalty = -0.020 * excess * outdoor_share * outdoor_hours
    cool_bonus = 0.022 * relief * outdoor_share * outdoor_hours
    # Rain is rare in Dubai and closes a terrace outright when it comes.
    rain_penalty = -0.55 * np.clip(precip_mm, 0, 3) / 3.0 * (0.35 + outdoor_share)
    # Even an enclosed site loses a little trade on a 45C afternoon: people stay home.
    citywide_heat = -0.004 * excess
    return np.clip(1.0 + heat_penalty + cool_bonus + rain_penalty + citywide_heat, 0.25, 1.9)


def ramadan_factor(hours: np.ndarray, is_ramadan: np.ndarray, intensity: float) -> np.ndarray:
    """Ramadan inverts the day rather than scaling it.

    Daytime trade collapses because most customers are fasting, and the hours
    after iftar carry the whole day. Modelling this as a single multiplier would
    average a collapse and a surge into approximately nothing, which is exactly
    the mistake a naive holiday flag makes.
    """
    day = (hours >= 5) & (hours < 18)
    iftar = (hours >= 18) & (hours < 24)
    late = (hours >= 0) & (hours < 2)
    f = np.ones_like(hours, dtype=float)
    f = np.where(is_ramadan & day, 1.0 - 0.70 * intensity, f)
    f = np.where(is_ramadan & iftar, 1.0 + 0.85 * intensity, f)
    f = np.where(is_ramadan & late, 1.0 + 1.10 * intensity, f)
    return f


def build(seed: int = SEED) -> tuple[list[FootfallRecord], dict]:
    brand = load_brand()
    conn = connect()
    rng = np.random.default_rng(seed)

    weather = {
        (r["zone_code"], r["ts_local"]): (r["apparent_c"], r["precip_mm"])
        for r in conn.execute(
            "SELECT zone_code, ts_local, apparent_c, precip_mm FROM weather_hourly"
        )
    }
    calendar = {
        r["date_local"]: dict(r)
        for r in conn.execute(
            "SELECT date_local, weekday, is_public_holiday, is_ramadan, is_school_break "
            "FROM calendar_days"
        )
    }
    # Event pull per zone-day, precomputed: sum of scale weights decayed by
    # distance, with citywide events applied at full strength everywhere.
    pull: dict[tuple[str, str], float] = {}
    for row in conn.execute(
        "SELECT e.start_date, e.end_date, e.scale_weight, e.venue_key, d.zone_code, d.distance_km "
        "FROM events e JOIN event_zone_distance d ON d.event_id = e.event_id"
    ):
        decay = (
            1.0
            if row["venue_key"] == "citywide"
            else float(np.exp(-row["distance_km"] / EVENT_DECAY_KM))
        )
        d0 = date.fromisoformat(row["start_date"])
        d1 = date.fromisoformat(row["end_date"])
        step = d0
        while step <= d1:
            key = (row["zone_code"], step.isoformat())
            pull[key] = pull.get(key, 0.0) + row["scale_weight"] * decay
            step += timedelta(days=1)

    days = sorted(calendar)
    start, end = days[0], days[-1]
    records: list[FootfallRecord] = []
    diagnostics: dict[str, dict] = {}

    for zone in brand.zones:
        shape = shape_for(zone.code, zone.opens, zone.closes)
        peak = (zone.seats + zone.outdoor_seats) * PEAK_PER_SEAT
        outdoor_share = zone.outdoor_share
        # Deira reshapes hardest through Ramadan; the mall sites least.
        ramadan_intensity = {"DXB-DEI": 1.0, "DXB-DTN": 0.55, "DXB-MOE": 0.6, "DXB-MAR": 0.75}[
            zone.code
        ]

        ts_list, hours, base = [], [], []
        app, pre, ram, hol, brk, evt, wdy, trd = [], [], [], [], [], [], [], []

        for i, day in enumerate(days):
            cal = calendar[day]
            d = date.fromisoformat(day)
            for hour in range(24):
                ts = f"{day}T{hour:02d}:00"
                a, p = weather.get((zone.code, ts), (None, None))
                if a is None:
                    continue
                ts_list.append(ts)
                hours.append(hour)
                base.append(peak * shape[hour])
                app.append(a)
                pre.append(p or 0.0)
                ram.append(bool(cal["is_ramadan"]))
                hol.append(bool(cal["is_public_holiday"]))
                brk.append(bool(cal["is_school_break"]))
                evt.append(pull.get((zone.code, day), 0.0))
                wdy.append(WEEKDAY_FACTOR[d.weekday()])
                trd.append(1.0 + i * 0.00018)

        h = np.array(hours)
        series = np.array(base)
        series *= np.array(wdy) * np.array(trd)
        series *= weather_factor(np.array(app), np.array(pre), outdoor_share, h)
        series *= ramadan_factor(h, np.array(ram), ramadan_intensity)
        # A public holiday lifts leisure trade and flattens the commuter peak.
        series *= np.where(np.array(hol), np.where(h < 11, 0.78, 1.22), 1.0)
        # The summer exodus: fewer people in the city at all.
        series *= np.where(np.array(brk), 0.88, 1.0)
        # Events pull, saturating — a second festival does not double the street.
        series *= 1.0 + 0.42 * np.tanh(np.array(evt))
        series *= rng.lognormal(-0.5 * 0.17**2, 0.17, size=series.size)

        counts = np.maximum(0, np.round(series)).astype(int)
        # Conversion is higher in the morning (a commuter buys) than in the
        # evening (a group sits), and is capped below 1 by construction.
        conv = np.where(h < 11, 0.72, np.where(h < 17, 0.58, 0.46))
        txns = np.minimum(counts, np.round(counts * conv).astype(int))

        for ts, c, t in zip(ts_list, counts, txns, strict=True):
            records.append(FootfallRecord(zone.code, ts, int(c), int(t)))

        diagnostics[zone.code] = {
            "outdoor_share": round(outdoor_share, 3),
            "peak_capacity_per_hour": round(peak, 1),
            "mean_footfall": round(float(counts.mean()), 2),
            "ramadan_intensity": ramadan_intensity,
        }

    return records, {"span": [start, end], "zones": diagnostics, "seed": seed}


def fit_temperature_slope(conn, zone_code: str) -> float:
    """OLS slope of footfall on apparent temperature, evening hours only.

    Evening hours only because that is when a terrace is used; over the whole
    day the enclosed sites' flat response would drown the signal in both.
    """
    rows = conn.execute(
        "SELECT f.footfall, w.apparent_c FROM footfall_hourly f "
        "JOIN weather_hourly w ON w.zone_code=f.zone_code AND w.ts_local=f.ts_local "
        "WHERE f.zone_code=? AND CAST(substr(f.ts_local,12,2) AS INTEGER) BETWEEN 18 AND 22",
        (zone_code,),
    ).fetchall()
    y = np.array([r["footfall"] for r in rows], dtype=float)
    x = np.array([r["apparent_c"] for r in rows], dtype=float)
    # Relative slope: percent of the zone's own mean per degree, so a big site
    # and a small one are comparable.
    slope = np.polyfit(x, y, 1)[0]
    return float(slope / y.mean())


def build_pos(seed: int = SEED, months: int = 12) -> list[BasketRecord]:
    """A basket-level sample for RFM, drawn from the generated footfall.

    Customers are given heterogeneous visit rates so the RFM segmentation in
    Phase B has real structure to find rather than a single Poisson blob.
    """
    brand = load_brand()
    conn = connect()
    rng = np.random.default_rng(seed + 1)

    end = date.fromisoformat(
        conn.execute(
            "SELECT MAX(date_local) FROM calendar_days WHERE date_local <= date('now')"
        ).fetchone()[0]
    )
    start = end - timedelta(days=int(months * 30.44))

    rows = conn.execute(
        "SELECT zone_code, ts_local, transactions FROM footfall_hourly "
        "WHERE ts_local >= ? AND ts_local <= ? AND transactions > 0",
        (start.isoformat(), end.isoformat() + "T23:59"),
    ).fetchall()

    # A customer base with a long tail: a few regulars, many one-visit tourists.
    n_customers = 2400
    loyalty = rng.lognormal(0.0, 1.05, size=n_customers)
    loyalty /= loyalty.sum()
    prices = {p.id: p.price_aed for p in brand.products}

    baskets: list[BasketRecord] = []
    for r in rows:
        # Sample a small fraction of transactions rather than all of them. A
        # pilot hands over an extract, not a till dump, and RFM needs enough
        # repeat visits per customer to be stable rather than enough rows to be
        # impressive — 0.008 gives roughly ten thousand baskets over 2,400
        # customers, which is the shape of a real sample export.
        n = rng.binomial(r["transactions"], 0.008)
        if n == 0:
            continue
        hour = int(r["ts_local"][11:13])
        dp = daypart_of(hour)
        for _ in range(n):
            cid = int(rng.choice(n_customers, p=loyalty))
            items = int(1 + rng.poisson(0.7))
            amount = float(
                np.round(sum(rng.choice(list(prices.values())) for _ in range(items)), 2)
            )
            baskets.append(
                BasketRecord(
                    basket_id=f"B{len(baskets):07d}",
                    customer_id=f"C{cid:05d}",
                    zone_code=r["zone_code"],
                    ts_local=r["ts_local"],
                    items=items,
                    amount_aed=amount,
                    daypart=dp,
                )
            )
    return baskets


def run(seed: int = SEED) -> dict:
    records, meta = build(seed)
    conn = connect()
    upsert_many(
        conn,
        "footfall_hourly",
        ("zone_code", "ts_local", "footfall", "transactions", "simulated"),
        [r.as_row() for r in records],
    )

    baskets = build_pos(seed)
    conn.execute("DELETE FROM pos_baskets")
    upsert_many(
        conn,
        "pos_baskets",
        (
            "basket_id",
            "customer_id",
            "zone_code",
            "ts_local",
            "items",
            "amount_aed",
            "daypart",
            "sample",
        ),
        [b.as_row() for b in baskets],
    )

    with CSV_OUT.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(
            (
                "basket_id",
                "customer_id",
                "zone_code",
                "ts_local",
                "items",
                "amount_aed",
                "daypart",
                "sample",
            )
        )
        w.writerows(b.as_row() for b in baskets)

    meta["footfall_rows"] = len(records)
    meta["baskets"] = len(baskets)
    return meta


def verify() -> int:
    brand = load_brand()
    conn = connect()
    r = Result(
        task="A7-footfall", dataset="footfall_hourly", generated_by="pipeline/footfall.py --verify"
    )

    per_zone = {
        row["zone_code"]: row["n"]
        for row in conn.execute(
            "SELECT zone_code, COUNT(*) n FROM footfall_hourly GROUP BY zone_code"
        )
    }
    slopes = {z.code: round(fit_temperature_slope(conn, z.code), 5) for z in brand.zones}
    outdoor = {z.code: round(z.outdoor_share, 3) for z in brand.zones}

    r.stats = {
        "rows": sum(per_zone.values()),
        "rows_per_zone": per_zone,
        "baskets": conn.execute("SELECT COUNT(*) FROM pos_baskets").fetchone()[0],
        "customers": conn.execute("SELECT COUNT(DISTINCT customer_id) FROM pos_baskets").fetchone()[
            0
        ],
        "outdoor_share": outdoor,
        "evening_temperature_slope_per_degree": slopes,
        "note": "slope is the fractional change in footfall per degree of apparent "
        "temperature, evening hours only",
    }

    r.check("all four zones present", set(per_zone) == {z.code for z in brand.zones})
    r.check(
        "every row is labelled simulated",
        conn.execute("SELECT COUNT(*) FROM footfall_hourly WHERE simulated!=1").fetchone()[0] == 0,
    )
    r.check(
        "transactions never exceed footfall",
        conn.execute(
            "SELECT COUNT(*) FROM footfall_hourly WHERE transactions > footfall"
        ).fetchone()[0]
        == 0,
    )

    # The claim the whole per-zone argument rests on, measured rather than assumed.
    r.check(
        "the outdoor site is more temperature-sensitive than the enclosed one",
        slopes["DXB-MAR"] < slopes["DXB-MOE"],
        f"Marina {slopes['DXB-MAR']}/degree vs Al Barsha {slopes['DXB-MOE']}/degree",
    )
    r.check(
        "temperature sensitivity orders by outdoor share",
        sorted(slopes, key=lambda z: slopes[z]) == sorted(outdoor, key=lambda z: -outdoor[z]),
        f"slope order {sorted(slopes, key=lambda z: slopes[z])} vs "
        f"outdoor order {sorted(outdoor, key=lambda z: -outdoor[z])}",
    )

    # Ramadan must invert the day, not scale it.
    ram = conn.execute(
        "SELECT AVG(CASE WHEN CAST(substr(f.ts_local,12,2) AS INTEGER) BETWEEN 8 AND 15 "
        "THEN f.footfall END) day_avg, "
        "AVG(CASE WHEN CAST(substr(f.ts_local,12,2) AS INTEGER) BETWEEN 19 AND 23 "
        "THEN f.footfall END) night_avg "
        "FROM footfall_hourly f JOIN calendar_days c ON c.date_local = substr(f.ts_local,1,10) "
        "WHERE c.is_ramadan=1 AND f.zone_code='DXB-DEI'"
    ).fetchone()
    normal = conn.execute(
        "SELECT AVG(CASE WHEN CAST(substr(f.ts_local,12,2) AS INTEGER) BETWEEN 8 AND 15 "
        "THEN f.footfall END) day_avg "
        "FROM footfall_hourly f JOIN calendar_days c ON c.date_local = substr(f.ts_local,1,10) "
        "WHERE c.is_ramadan=0 AND f.zone_code='DXB-DEI'"
    ).fetchone()
    r.stats["ramadan_deira"] = {
        "daytime_avg": round(ram["day_avg"], 1),
        "evening_avg": round(ram["night_avg"], 1),
        "non_ramadan_daytime_avg": round(normal["day_avg"], 1),
    }
    r.check(
        "Ramadan collapses daytime trade at Deira",
        ram["day_avg"] < normal["day_avg"] * 0.6,
        f"{ram['day_avg']:.0f} vs {normal['day_avg']:.0f} normally",
    )
    r.check(
        "Ramadan evenings exceed Ramadan daytime at Deira",
        ram["night_avg"] > ram["day_avg"],
        f"{ram['night_avg']:.0f} after iftar vs {ram['day_avg']:.0f} in the day",
    )

    r.check(
        "the POS sample has a customer base with a tail",
        r.stats["customers"] > 1000,
        f"{r.stats['customers']} customers",
    )

    # Found by inspecting the generated CSV rather than by a test: the daypart
    # lobes are Gaussians with no natural zero, so a shut cafe traded a trickle
    # at 04:00 and it reached the sample export.
    closed = conn.execute("SELECT COUNT(*) FROM pos_baskets WHERE daypart='closed'").fetchone()[0]
    r.stats["baskets_by_daypart"] = {
        row["daypart"]: row["n"]
        for row in conn.execute(
            "SELECT daypart, COUNT(*) n FROM pos_baskets GROUP BY daypart ORDER BY n DESC"
        )
    }
    r.check("no basket falls outside trading hours", closed == 0, f"{closed} closed-hour baskets")
    r.check(
        "the evening daypart is the largest, as the brand kit claims",
        max(r.stats["baskets_by_daypart"], key=r.stats["baskets_by_daypart"].get) == "evening",
        str(r.stats["baskets_by_daypart"]),
    )
    return r.report()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()
    if not args.verify:
        meta = run(args.seed)
        print(
            f"footfall: {meta['footfall_rows']:,} rows, {meta['baskets']:,} baskets "
            f"(seed {meta['seed']}), csv at {CSV_OUT.relative_to(ROOT)}"
        )
        return 0
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
