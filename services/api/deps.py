"""Shared FastAPI dependencies."""

from __future__ import annotations

import sqlite3
from functools import lru_cache

from services.api.core.db import connect


@lru_cache(maxsize=1)
def _conn() -> sqlite3.Connection:
    return connect()


def db() -> sqlite3.Connection:
    """One connection for the process.

    SQLite in WAL mode handles concurrent readers, and every write in this
    application goes through the pipelines rather than through a request, so a
    pool would be machinery with nothing to manage.
    """
    return _conn()
