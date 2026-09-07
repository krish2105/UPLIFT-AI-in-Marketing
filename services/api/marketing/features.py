"""The feature matrix: one row per zone-hour, with every driver attached.

WHAT A FEATURE IS ALLOWED TO KNOW
---------------------------------
Every column here is knowable BEFORE the hour it describes. Weather is a
forecast, the calendar is fixed, events are announced in advance. Nothing is
derived from the footfall being predicted, and nothing is derived from a future
row.

That sounds obvious and is the single easiest way to produce a model that scores
beautifully and cannot forecast. The lag features below are the place it would
happen, so they are built by shifting the series and are asserted in
tests/marketing/test_features.py to contain no information from their own hour.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

import numpy as np
import pandas as pd

#: Every column the model sees, in a fixed order so a saved model and a fresh
#: frame cannot silently disagree about which column is which.
FEATURES: tuple[str, ...] = (
    "hour",
    "dow",
    "is_weekend",
    "is_public_holiday",
    "is_ramadan",
    "ramadan_day",
    "is_school_break",
    "temp_c",
    "apparent_c",
    "humidity",
    "precip_mm",
    "wind_kmh",
    "event_pull",
    "days_to_event",
    "trend",
    "lag_168",
    "lag_336",
    "roll_168_mean",
)

TARGET = "footfall"


@dataclass(frozen=True)
class Frame:
    """A zone's modelling frame, already sorted by time."""

    zone: str
    df: pd.DataFrame

    def split(self, holdout_days: int) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Split by TIME, never at random.

        A random split lets the model see next Tuesday while predicting last
        Tuesday, which on an hourly series with a weekly cycle is close to
        giving it the answer. Every score in this project comes from a
        chronological holdout.
        """
        cutoff = self.df["ts"].max() - pd.Timedelta(days=holdout_days)
        return self.df[self.df["ts"] <= cutoff], self.df[self.df["ts"] > cutoff]


def load_frame(conn: sqlite3.Connection, zone: str) -> Frame:
    footfall = pd.read_sql_query(
        "SELECT ts_local AS ts, footfall, transactions FROM footfall_hourly "
        "WHERE zone_code = ? ORDER BY ts_local",
        conn,
        params=(zone,),
    )
    weather = pd.read_sql_query(
        "SELECT ts_local AS ts, temp_c, apparent_c, humidity, precip_mm, wind_kmh "
        "FROM weather_hourly WHERE zone_code = ?",
        conn,
        params=(zone,),
    )
    calendar = pd.read_sql_query(
        "SELECT date_local AS d, weekday, is_weekend, is_public_holiday, is_ramadan, "
        "ramadan_day, is_school_break FROM calendar_days",
        conn,
    )
    events = pd.read_sql_query(
        "SELECT e.start_date, e.end_date, e.scale_weight, e.venue_key, d.distance_km "
        "FROM events e JOIN event_zone_distance d ON d.event_id = e.event_id "
        "WHERE d.zone_code = ?",
        conn,
        params=(zone,),
    )

    df = footfall.merge(weather, on="ts", how="inner")
    df["ts"] = pd.to_datetime(df["ts"])
    df["d"] = df["ts"].dt.strftime("%Y-%m-%d")
    df = df.merge(calendar, on="d", how="left")

    df["hour"] = df["ts"].dt.hour
    df["dow"] = df["ts"].dt.dayofweek
    df["ramadan_day"] = df["ramadan_day"].fillna(0)
    for col in ("is_weekend", "is_public_holiday", "is_ramadan", "is_school_break"):
        df[col] = df[col].fillna(0).astype(int)

    pull, ahead = _event_features(events, df["d"].unique())
    df["event_pull"] = df["d"].map(pull).fillna(0.0)
    #: Capped at 30: a festival five weeks out does not move a coffee counter,
    #: and an uncapped countdown would let the model learn the calendar's edge.
    df["days_to_event"] = df["d"].map(ahead).fillna(30).clip(0, 30)

    df["trend"] = np.arange(len(df), dtype=float) / max(len(df), 1)

    # Lags are the previous week and the one before it — the same hour of the
    # same weekday, which is the structure an hourly retail series actually has.
    df["lag_168"] = df[TARGET].shift(168)
    df["lag_336"] = df[TARGET].shift(336)
    df["roll_168_mean"] = df[TARGET].shift(1).rolling(168, min_periods=24).mean()

    df = df.dropna(subset=["lag_168", "lag_336", "roll_168_mean"]).reset_index(drop=True)
    return Frame(zone=zone, df=df)


def _event_features(events: pd.DataFrame, days) -> tuple[dict, dict]:
    """Pull per day, and days until the next event of any size.

    Citywide events apply at full strength everywhere; everything else decays
    with distance from the site. Six kilometres is the decay constant — beyond
    roughly eight, a Dubai event does not move a neighbourhood counter.
    """
    pull: dict[str, float] = {}
    starts: list[tuple[pd.Timestamp, float]] = []
    for row in events.itertuples():
        decay = 1.0 if row.venue_key == "citywide" else float(np.exp(-row.distance_km / 6.0))
        weight = row.scale_weight * decay
        span = pd.date_range(row.start_date, row.end_date, freq="D")
        for day in span:
            key = day.strftime("%Y-%m-%d")
            pull[key] = pull.get(key, 0.0) + weight
        starts.append((pd.Timestamp(row.start_date), weight))

    starts.sort()
    start_days = np.array([s.value for s, _ in starts])
    ahead: dict[str, float] = {}
    for day in days:
        t = pd.Timestamp(day).value
        future = start_days[start_days >= t]
        ahead[day] = (future[0] - t) / 86_400_000_000_000 if len(future) else 30.0
    return pull, ahead
