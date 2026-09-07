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
