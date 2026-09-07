"""The corpus, and lexical retrieval over it.

WHY BM25 AND NOT A VECTOR STORE, YET
------------------------------------
The A9 spike chose bge-m3 for cross-lingual retrieval and that is the Phase C
plan. What is here now is BM25, and it is not a placeholder: it is the half of a
hybrid retriever that never needs a model, it runs on a free dyno with no
embedder, and it makes the citation contract testable before any inference is
involved. Phase C fuses vectors into this, it does not replace it.

WHAT IS IN THE CORPUS
---------------------
Only things this project can quote: the brand kit's own rules and voice, the
dataset registry's provenance, and the measured results. Every passage carries
the file it came from, so an answer that cannot cite is an answer that is not
returned.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from rank_bm25 import BM25Okapi

from services.api.brand import load_brand
from services.api.data.registry import REGISTRY

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "docs" / "results"


@dataclass(frozen=True)
class Passage:
    id: str
    text: str
    source: str
    source_url: str
    kind: str  # "rule" | "voice" | "dataset" | "result" | "brand"
    trust: str = "project"  # everything here is authored or measured by this project


def _tokenise(text: str) -> list[str]:
    """Latin, Arabic and Devanagari all tokenise on the same word-character
    class here; a language-specific stemmer would help English and hurt the
    other two, so none is used."""
    return re.findall(r"[\w؀-ۿऀ-ॿ]+", text.lower())


@lru_cache(maxsize=1)
def build() -> tuple[list[Passage], BM25Okapi]:
    brand = load_brand()
    passages: list[Passage] = []

    passages.append(
        Passage(
            id="brand-identity",
            text=(
                f"{brand.name} is a fictional Dubai speciality coffee and bakery chain with four "
                f"locations, invented for this coursework demonstration. {brand.disclaimer} "
                f"{brand.raw['identity']['positioning']} {brand.raw['identity']['proposition']}"
            ),
            source="data/brand/sidra.yaml",
            source_url="docs/brand/SIDRA-brand-guidelines.pdf",
            kind="brand",
        )
    )

    for z in brand.zones:
        passages.append(
            Passage(
                id=f"zone-{z.code}",
                text=(
                    f"{z.code} {z.name} at {z.site}. {z.character}. {z.demand_notes} "
                    f"It has {z.seats} indoor and {z.outdoor_seats} outdoor seats "
                    f"({round(z.outdoor_share * 100)} percent outdoors) and trades "
                    f"{z.opens} to {z.closes}."
                ),
                source="data/brand/sidra.yaml",
                source_url="docs/brand/SIDRA-brand-guidelines.pdf",
                kind="brand",
            )
        )

    for principle in brand.voice["principles"] + brand.voice["do"] + brand.voice["dont"]:
        passages.append(
            Passage(
                id=f"voice-{len(passages)}",
                text=principle,
                source="SIDRA brand guidelines, voice",
                source_url="docs/brand/SIDRA-brand-guidelines.pdf",
                kind="voice",
            )
        )

    for r in brand.claims_to_avoid:
        src = brand.sources[r.source]
        passages.append(
            Passage(
                id=r.id,
                text=(
                    f"{r.id} ({r.family}, {r.severity}). {r.why.strip()} "
                    f"Triggers: {', '.join(r.patterns) or 'presence check'}. "
                    f"Source: {src.citation()}, clause: {r.clause}."
                    + (
                        f' Quoted: "{r.clause_quote.strip()}"'
                        if r.clause_verified
                        else " This clause has not yet been read verbatim from the source."
                    )
                ),
                source=src.citation(),
                source_url=src.url,
                kind="rule",
            )
        )

    for d in REGISTRY:
        passages.append(
            Passage(
                id=f"dataset-{d.key}",
                text=(
                    f"{d.title} ({d.key}) is labelled {d.label.value}. {d.description} "
                    f"{d.label.caveat} Licence: {d.licence}. Source: {d.source_name}, "
                    f"verified {d.verified}. Built by {d.built_by}."
                ),
                source="docs/datasets.md",
                source_url=d.source_url,
                kind="dataset",
            )
        )

    for path in sorted(RESULTS.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        bits = [
            str(payload.get(k))
            for k in (
                "method",
                "note_on_smape",
                "note_on_bias",
                "note_on_parameters",
                "note_on_curves",
                "note_on_language",
                "note_on_precision",
            )
            if payload.get(k)
        ]
        if not bits:
            continue
        passages.append(
            Passage(
                id=f"result-{path.stem}",
                text=f"{path.stem}: " + " ".join(bits),
                source=f"docs/results/{path.name}",
                source_url=f"docs/results/{path.name}",
                kind="result",
            )
        )

    index = BM25Okapi([_tokenise(p.text) for p in passages])
    return passages, index


def search(query: str, k: int = 5) -> list[dict]:
    passages, index = build()
    scores = index.get_scores(_tokenise(query))
    order = sorted(range(len(passages)), key=lambda i: -scores[i])[:k]
    out = []
    for rank, i in enumerate(order, 1):
        if scores[i] <= 0:
            continue
        p = passages[i]
        out.append(
            {
                "rank": rank,
                "id": p.id,
                "score": round(float(scores[i]), 3),
                "text": p.text,
                "source": p.source,
                "source_url": p.source_url,
                "kind": p.kind,
            }
        )
    return out


def answer(query: str, k: int = 4) -> dict:
    """Retrieve, and refuse rather than guess.

    There is no generation step here. An answer is the passages that matched,
    with their sources — which is less satisfying than a paragraph and cannot
    fabricate. Phase C adds a model that writes prose over exactly these
    passages and is forbidden from adding a sentence without one.
    """
    hits = search(query, k)
    return {
        "query": query,
        "answered": bool(hits),
        "citations": hits,
        "note": (
            "Lexical retrieval over the project's own corpus — the brand kit, the dataset "
            "registry and the measured results. There is no generation step: an answer is "
            "the passages that matched, with their sources. Phase C adds a model that "
            "writes over exactly these passages and cannot add a sentence without one."
        )
        if hits
        else (
            "Nothing in the corpus matched. That is the correct answer to a question this "
            "project cannot cite, and it is returned rather than a plausible paragraph."
        ),
        "corpus_size": len(build()[0]),
    }
