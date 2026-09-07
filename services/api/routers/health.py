"""Liveness, and an honest account of what this instance can actually do."""

from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter, Depends

from services.api import APP, BRAND, BRAND_IS_FICTIONAL, COURSE
from services.api.data.registry import REGISTRY
from services.api.deps import db
from services.api.rag import vectors

router = APIRouter(tags=["health"])


@router.get("/healthz", summary="Liveness and capability")
def healthz(conn: sqlite3.Connection = Depends(db)) -> dict:
    """Reports which datasets are actually loaded.

    A deployed instance with an ephemeral filesystem can come up with an empty
    database, and a health check that returns "ok" in that state is worse than
    no health check. So this says what is present rather than only that the
    process is running.
    """
    loaded = {}
    for d in REGISTRY:
        try:
            loaded[d.key] = conn.execute(f"SELECT COUNT(*) FROM {d.table}").fetchone()[0]
        except sqlite3.OperationalError:
            loaded[d.key] = 0

    # Retrieval quality changes silently with the environment: the same code
    # answers an Arabic question differently on a laptop with Ollama than on a
    # free instance with neither a model nor a key. Saying which mode is live is
    # the difference between a reader judging the retriever and guessing at it.
    return {
        "status": "ok" if all(loaded.values()) else "degraded",
        "retrieval": vectors.describe(),
        "app": APP,
        "course": COURSE,
        "brand": {"name": BRAND, "fictional": BRAND_IS_FICTIONAL},
        "datasets_loaded": loaded,
        "empty_datasets": [k for k, v in loaded.items() if v == 0],
        "database": os.getenv("UPLIFT_DB", "data/processed/uplift.db"),
    }
