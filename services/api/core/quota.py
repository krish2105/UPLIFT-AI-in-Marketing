"""Budgets counted as REQUESTS, not tokens.

A token budget this project cannot measure is theatre. The free tiers UPLIFT
runs on do not return trustworthy token accounting, and a number the project
cannot verify has no business appearing in a report — the same rule that governs
every other figure here. A request count is exact, free to measure, and the
thing the free tiers actually rate-limit on.

Exhaustion is NOT an error. It degrades the chain to the next provider, which is
why `consume` returns a bool rather than raising: running out of Gemini calls is
an operational fact, not a failure the caller should have to handle.
"""

from __future__ import annotations

import os
import sqlite3
import threading

from services.api.core.db import WRITE_LOCK


class Quota:
    """Per-provider request budget, optionally persisted.

    Pass a sqlite3 connection to survive a restart; without one the counts live
    for the life of the process, which is what tests want.
    """

    def __init__(self, limits: dict[str, int], conn: sqlite3.Connection | None = None) -> None:
        self._limits = dict(limits)
        self._conn = conn
        self._lock = threading.Lock()
        self._used: dict[str, int] = {}
        if conn is not None:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS quotas "
                "(provider TEXT PRIMARY KEY, used INTEGER NOT NULL)"
            )
            conn.commit()
            for provider, used in conn.execute("SELECT provider, used FROM quotas"):
                self._used[provider] = used

    @classmethod
    def from_env(cls, conn: sqlite3.Connection | None = None) -> Quota:
        """The deployed budgets. Local providers are unmetered because they cost
        nothing but electricity; the stub is unmetered because it is arithmetic."""
        return cls(
            {
                "ollama": 1_000_000,
                "gemini": int(os.getenv("QUOTA_GEMINI_REQUESTS", "200")),
                "groq": int(os.getenv("QUOTA_GROQ_REQUESTS", "200")),
                "anthropic": 0,  # present and permanently unusable; see llm.py
                "stub": 1_000_000,
            },
            conn,
        )

    def limit(self, provider: str) -> int:
        return self._limits.get(provider, 0)

    def remaining(self, provider: str) -> int:
        return max(0, self.limit(provider) - self._used.get(provider, 0))

    def consume(self, provider: str) -> bool:
        """Spend one request. False when the budget is already spent."""
        with self._lock:
            if self.remaining(provider) <= 0:
                return False
            self._used[provider] = self._used.get(provider, 0) + 1
            if self._conn is not None:
                with WRITE_LOCK:
                    self._conn.execute(
                        "INSERT INTO quotas(provider, used) VALUES(?, ?) "
                        "ON CONFLICT(provider) DO UPDATE SET used = excluded.used",
                        (provider, self._used[provider]),
                    )
                    self._conn.commit()
            return True

    def reset(self, provider: str | None = None) -> None:
        with self._lock:
            if provider is None:
                self._used.clear()
            else:
                self._used.pop(provider, None)

    def as_dict(self) -> dict[str, dict[str, int]]:
        return {
            p: {
                "limit": self.limit(p),
                "used": self._used.get(p, 0),
                "remaining": self.remaining(p),
            }
            for p in self._limits
        }
