"""The vector half of the retriever, and an honest account of when it exists.

WHY THIS IS NOT A VECTOR DATABASE
---------------------------------
`sqlite-vec` was in the dependency list from the first commit and never
imported, which is the most common way a dependency lies: it names an intention
rather than a fact. Its value is approximate nearest neighbours over a corpus
too large to scan. This corpus is 39 passages. An ANN index over 39 rows is
slower than the scan it replaces, and it would have been there to make the
architecture diagram look right.

So the search is an exact cosine over a small matrix, and the dependency is
gone. If the corpus ever reaches the tens of thousands, the index earns its
place then — and `search()` is the only function that changes.

WHEN VECTORS EXIST AT ALL, AND WHY ONLY LOCALLY
----------------------------------------------
Only when something can embed the QUERY at request time. Passage vectors can be
precomputed; a query arrives when it arrives. That embedder is Ollama on this
machine — bge-m3, which the A9 spike chose on cross-lingual margin over a
control — or nothing.

A hosted embedding endpoint was written first and removed. It was allowed by the
plan, and `tests/invariants/test_no_side_effects.py` failed on it, which was the
right outcome: embedding a query means SENDING THE QUERY, so every question a
user typed would have left the deployed instance for a third party. ASI-01 says
this application takes no action outside its own process, and quietly amending
that claim for a re-ranking improvement is the trade the invariant exists to
block. It is also a poor trade on the measurement — `spike_retrieval.py` shows
the vector half cannot admit a passage on its own here, so what was on offer was
re-ordering results the words had already found.

So: the only network call in this module is to a loopback address, and
`_require_loopback` enforces that rather than trusting the comment. Deployed,
there is no embedder and retrieval is lexical — which `/healthz` reports, rather
than leaving a reader to infer the mode from the quality of the answers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

import httpx
import numpy as np

OLLAMA_MODEL = os.getenv("UPLIFT_EMBED_MODEL", "bge-m3:567m")

LOOPBACK = ("localhost", "127.0.0.1", "::1", "[::1]", "0.0.0.0")


class NotLoopbackError(RuntimeError):
    """OLLAMA_HOST pointed somewhere other than this machine.

    Raised rather than warned. A remote embedder would send every user query off
    the box, and an environment variable is not the place to make that decision
    silently — an operator who genuinely wants it has to change this code and
    face the invariant test that guards it.
    """


def _require_loopback(host: str) -> str:
    hostname = urlparse(host).hostname or ""
    if hostname not in LOOPBACK:
        raise NotLoopbackError(
            f"OLLAMA_HOST is {host!r}; embedding sends the user's query, so this module "
            f"only talks to {LOOPBACK}. See ASI-01 on the Security tab."
        )
    return host


@dataclass(frozen=True)
class Embedder:
    name: str
    model: str
    dim: int


class _Ollama:
    kind = "ollama"

    def __init__(self) -> None:
        self.host = _require_loopback(
            (os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
        )
        self.model = OLLAMA_MODEL

    def available(self) -> bool:
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=2.0)
            return r.status_code == 200 and any(
                m.get("name", "").startswith(self.model.split(":")[0])
                for m in r.json().get("models", [])
            )
        except (httpx.HTTPError, ValueError):
            return False

    def embed(self, texts: list[str]) -> np.ndarray:
        r = httpx.post(
            f"{self.host}/api/embed",
            json={"model": self.model, "input": texts},
            timeout=180.0,
        )
        r.raise_for_status()
        return np.asarray(r.json()["embeddings"], dtype=np.float32)


@lru_cache(maxsize=1)
def embedder():
    """The first embedder that can actually answer, or None.

    Order is free-first and local-first, the same rule the chat chain follows:
    a model on this machine costs nothing and leaks nothing.
    """
    for candidate in (_Ollama(),):
        try:
            if candidate.available():
                return candidate
        except Exception:  # noqa: BLE001 — an embedder that raises is an embedder that is absent
            continue
    return None


def mode() -> str:
    e = embedder()
    return "hybrid" if e else "lexical"


def describe() -> dict:
    e = embedder()
    return {
        "retrieval": mode(),
        "embedder": None if e is None else {"backend": e.kind, "model": e.model},
        "note": (
            "Lexical BM25 fused with exact cosine over passage embeddings."
            if e
            else "Lexical BM25 only — there is no local embedder, and this application "
            "will not send a query to a hosted one. The corpus is the project's own "
            "vocabulary, which BM25 handles; what is lost is re-ranking, and on the "
            "measurement in docs/results/C2-retrieval.json that is all it was doing."
        ),
    }


def cosine(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Cosine similarity of one vector against many, normalised defensively.

    A zero vector is not impossible — an embedder handed an empty passage
    returns one — and dividing by its norm yields nan, which sorts
    unpredictably and silently poisons the ranking.
    """
    qn = np.linalg.norm(query) or 1.0
    mn = np.linalg.norm(matrix, axis=1)
    mn[mn == 0] = 1.0
    return (matrix @ query) / (mn * qn)
