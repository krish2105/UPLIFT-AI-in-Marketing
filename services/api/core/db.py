"""SQLite, one file, no server.

WHY SQLITE AND NOT POSTGRES
---------------------------
The whole dataset is about a hundred thousand rows of hourly series and a few
thousand events. That fits comfortably in a file, and a file can be rebuilt
from the pipelines in under a minute, which matters more here than durability:
the deployed instance is a free Render dyno with an ephemeral filesystem, so
the database is a cache of the pipelines rather than a system of record. The
pipelines and the sources they cite are the system of record.

MIGRATIONS ARE A LIST, NOT A LIBRARY
------------------------------------
Each migration is applied once, in order, tracked in `schema_migrations`. A
migration is never edited after it ships — a change is a new entry. That is the
whole mechanism; anything more would be machinery this project does not need.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB = ROOT / "data" / "processed" / "uplift.db"

#: SQLite serialises writers itself, but concurrent writers from FastAPI's
#: threadpool still surface as "database is locked" under load. One process-wide
#: lock around writes is cheaper than tuning busy_timeout and easier to reason
#: about at this scale.
WRITE_LOCK = threading.Lock()

MIGRATIONS: list[tuple[str, str]] = [
    (
        "0001_weather",
        """
        CREATE TABLE IF NOT EXISTS weather_hourly (
            zone_code   TEXT    NOT NULL,
            ts_local    TEXT    NOT NULL,   -- ISO8601, Asia/Dubai, hour resolution
            temp_c      REAL,
            apparent_c  REAL,
            humidity    REAL,
            precip_mm   REAL,
            wind_kmh    REAL,
            source      TEXT    NOT NULL,   -- 'archive' | 'forecast'
            PRIMARY KEY (zone_code, ts_local)
        );
        CREATE INDEX IF NOT EXISTS ix_weather_ts ON weather_hourly (ts_local);
        """,
    ),
    (
        "0002_calendar",
        """
        CREATE TABLE IF NOT EXISTS calendar_days (
            date_local        TEXT PRIMARY KEY,   -- ISO date, Asia/Dubai
            weekday           INTEGER NOT NULL,   -- Monday=0 .. Sunday=6
            is_weekend        INTEGER NOT NULL,   -- UAE weekend is Sat+Sun
            is_public_holiday INTEGER NOT NULL,
            holiday_name      TEXT,
            holiday_kind      TEXT,               -- 'gregorian' | 'islamic'
            -- Islamic dates are set by moon sighting, so a calculated date can
            -- be a day out. Carried per row rather than assumed downstream.
            date_uncertainty_days INTEGER NOT NULL DEFAULT 0,
            is_ramadan        INTEGER NOT NULL,
            ramadan_day       INTEGER,
            is_school_break   INTEGER NOT NULL,
            school_break_name TEXT,
            -- Two different claims, deliberately not one column. A Gregorian
            -- holiday falling inside an approximate school-break window is
            -- still a certain date, and collapsing these made New Year's Day
            -- read as approximate.
            confidence            TEXT NOT NULL,  -- the holiday: observed | calculated
            school_break_confidence TEXT          -- the break window: approximate
        );
        CREATE INDEX IF NOT EXISTS ix_calendar_holiday ON calendar_days (is_public_holiday);
        """,
    ),
    (
        "0003_events",
        """
        CREATE TABLE IF NOT EXISTS events (
            event_id        TEXT PRIMARY KEY,
            series_key      TEXT NOT NULL,
            title           TEXT NOT NULL,
            category        TEXT NOT NULL,
            venue_key       TEXT NOT NULL,
            venue_name      TEXT NOT NULL,
            lat             REAL NOT NULL,
            lon             REAL NOT NULL,
            start_date      TEXT NOT NULL,
            end_date        TEXT NOT NULL,
            days            INTEGER NOT NULL,
            scale           TEXT NOT NULL,
            scale_weight    REAL NOT NULL,
            -- Always 1. Present as a column rather than as documentation so a
            -- query cannot return an event without seeing how it was sourced.
            curated         INTEGER NOT NULL,
            date_confidence TEXT NOT NULL,
            source_url      TEXT NOT NULL,
            licence         TEXT NOT NULL,
            wikipedia_title TEXT,
            wikipedia_extract TEXT,
            wikipedia_url   TEXT,
            segment_of      TEXT
        );
        CREATE INDEX IF NOT EXISTS ix_events_start ON events (start_date);
        CREATE INDEX IF NOT EXISTS ix_events_series ON events (series_key);

        CREATE TABLE IF NOT EXISTS event_zone_distance (
            event_id    TEXT NOT NULL,
            zone_code   TEXT NOT NULL,
            distance_km REAL NOT NULL,
            PRIMARY KEY (event_id, zone_code)
        );
        """,
    ),
    (
        "0004_footfall",
        """
        CREATE TABLE IF NOT EXISTS footfall_hourly (
            zone_code    TEXT    NOT NULL,
            ts_local     TEXT    NOT NULL,
            footfall     INTEGER NOT NULL,
            transactions INTEGER NOT NULL,
            -- Always 1, and NOT NULL, so no query can return this series
            -- without the column that says it is not observed.
            simulated    INTEGER NOT NULL CHECK (simulated = 1),
            PRIMARY KEY (zone_code, ts_local)
        );
        CREATE INDEX IF NOT EXISTS ix_footfall_ts ON footfall_hourly (ts_local);

        CREATE TABLE IF NOT EXISTS pos_baskets (
            basket_id   TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            zone_code   TEXT NOT NULL,
            ts_local    TEXT NOT NULL,
            items       INTEGER NOT NULL,
            amount_aed  REAL NOT NULL,
            daypart     TEXT NOT NULL,
            sample      INTEGER NOT NULL CHECK (sample = 1)
        );
        CREATE INDEX IF NOT EXISTS ix_pos_customer ON pos_baskets (customer_id);
        CREATE INDEX IF NOT EXISTS ix_pos_ts ON pos_baskets (ts_local);
        """,
    ),
]


def connect(path: str | Path | None = None) -> sqlite3.Connection:
    """Open the database, applying any migration not yet applied."""
    target = Path(path or os.getenv("UPLIFT_DB") or DEFAULT_DB)
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL lets a reader run while the pipelines write, which is what makes it
    # possible to refresh data without stopping the API.
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn)
    return conn


def migrate(conn: sqlite3.Connection) -> list[str]:
    conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (name TEXT PRIMARY KEY)")
    applied = {r[0] for r in conn.execute("SELECT name FROM schema_migrations")}
    ran: list[str] = []
    with WRITE_LOCK:
        for name, sql in MIGRATIONS:
            if name in applied:
                continue
            conn.executescript(sql)
            conn.execute("INSERT INTO schema_migrations(name) VALUES (?)", (name,))
            conn.commit()
            ran.append(name)
    return ran


def upsert_many(
    conn: sqlite3.Connection, table: str, columns: Iterable[str], rows: Iterable[tuple]
) -> int:
    """Insert-or-replace in one transaction. Returns the row count written."""
    cols = list(columns)
    placeholders = ",".join("?" * len(cols))
    sql = f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({placeholders})"
    batch = list(rows)
    with WRITE_LOCK:
        conn.executemany(sql, batch)
        conn.commit()
    return len(batch)
