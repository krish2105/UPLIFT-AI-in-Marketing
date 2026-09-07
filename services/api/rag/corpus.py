"""The corpus, and lexical retrieval over it.

LEXICAL FIRST, VECTORS WHEN THEY EXIST
-------------------------------------
BM25 is the half that never needs a model. It runs on a free instance with no
embedder and it makes the citation contract testable before any inference is
involved, so it is the floor rather than a fallback.

The vector half is fused on top when something can embed a query — Ollama here,
Gemini's free endpoint on a deployment that has a key, nothing on one that does
not. See `vectors.py` for why that is a real distinction and not a shrug: the
two halves fail differently. BM25 misses an Arabic question aimed at an English
passage; cosine drifts toward passages that are merely on-topic. Reciprocal rank
fusion takes agreement between them rather than trusting either score, which is
also why no score normalisation appears anywhere below — RRF reads ranks, and
ranks are the one thing the two methods produce on the same scale.

`/healthz` reports which mode is live, because "the answers got better" is not
something a reader should have to infer.

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

import numpy as np
from rank_bm25 import BM25Okapi

from services.api.brand import load_brand
from services.api.data.registry import REGISTRY
from services.api.rag import vectors

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


@lru_cache(maxsize=1)
def _passage_vectors():
    """Embed the corpus once per process, or return None.

    Cached rather than persisted: 39 passages take under a second on a local
    model, and a cache on disk would have to be invalidated whenever the brand
    kit, the registry or any result changed — three inputs that change often, in
    a project whose whole claim is that documents track their results. A stale
    vector is worse than a recomputed one.
    """
    e = vectors.embedder()
    if e is None:
        return None
    passages, _ = build()
    try:
        return e.embed([p.text for p in passages])
    except Exception:  # noqa: BLE001
        # An embedder that was reachable at startup and is not reachable now
        # degrades to lexical rather than failing the request. Retrieval that
        # returns fewer good answers beats retrieval that returns a 500.
        return None


# RRF's constant. 60 is the value from the original paper and it is not tuned
# here: with two retrievers there is nothing to tune it against that would not
# be fitting the constant to the handful of queries used to check it.
RRF_K = 60


# A lexical vote needs more than one query word behind it.
#
# Rule passages carry their own regex triggers, which is what lets "is detox
# allowed?" find the rule that bans it. The cost: a trigger fragment can be a
# common word in its own language and rare in THIS corpus, so IDF reads it as
# highly distinctive. A Hindi question about weather matched the medicinal-
# claims rule on `करता` — an auxiliary verb, roughly "does" — and matched
# NOTHING else, yet scored top because it was the only lexical hit at all. RRF
# then promoted it above the passage that answered, since agreement between two
# lists beats one list's first place.
#
# Gating on score share does not catch this: the spurious hit IS the maximum,
# so it clears any share of itself. What is actually wrong is coverage — one
# word out of six. So a passage votes lexically only when it carries at least
# two distinct query terms, and a one- or two-word query keeps the single-term
# path it needs.
MIN_TERMS_FOR_LEXICAL_VOTE = 2

# Function words, excluded from COVERAGE COUNTING only — BM25 still scores the
# whole query, and these are not stripped from any passage.
#
# The list exists because coverage was counting grammar as evidence. "What is
# the capital of Peru" shares four words with half the corpus and answers
# nothing; the Hindi `करता` and the English `this` are the same bug wearing
# different scripts, which is why all three languages are here rather than
# English alone. It is deliberately short: a long stopword list starts deciding
# which content words matter, and this one is only allowed to decide which words
# are not content at all.
_STOP_EN_AR_HI_EN = (
    "a",
    "an",
    "the",
    "this",
    "that",
    "these",
    "those",
    "of",
    "in",
    "on",
    "at",
    "to",
    "for",
    "from",
    "by",
    "with",
    "and",
    "or",
    "but",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "it",
    "its",
    "as",
    "what",
    "which",
    "who",
    "whom",
    "whose",
    "when",
    "where",
    "why",
    "how",
    "i",
    "you",
    "he",
    "she",
    "they",
    "we",
    "me",
    "my",
    "your",
    "our",
    "their",
    "there",
    "here",
    "not",
    "no",
    "yes",
    "can",
    "could",
    "would",
    "should",
    "will",
    "shall",
    "may",
    "might",
    "must",
    "about",
    "into",
    "over",
    "under",
    "than",
    "then",
    "so",
    "if",
)

_STOP_EN_AR_HI_AR = (
    "من",
    "في",
    "على",
    "عن",
    "إلى",
    "مع",
    "هل",
    "ما",
    "ماذا",
    "هي",
    "هو",
    "هم",
    "كان",
    "يكون",
    "التي",
    "الذي",
    "و",
    "أو",
    "ثم",
    "كيف",
    "متى",
    "أين",
    "لماذا",
    "هذا",
    "هذه",
    "ذلك",
)

_STOP_EN_AR_HI_HI = (
    "का",
    "की",
    "के",
    "को",
    "में",
    "से",
    "पर",
    "है",
    "हैं",
    "था",
    "थे",
    "यह",
    "वह",
    "क्या",
    "कौन",
    "कब",
    "कहाँ",
    "क्यों",
    "कैसे",
    "और",
    "या",
    "तो",
    "एक",
    "कि",
    "जो",
    "करता",
    "करती",
    "करते",
)

STOPWORDS = frozenset(_STOP_EN_AR_HI_EN + _STOP_EN_AR_HI_AR + _STOP_EN_AR_HI_HI)


@lru_cache(maxsize=1)
def _vector_admission_bar() -> float | None:
    """The similarity a passage must reach before the vector half may admit it
    to an answer on its own — measured, not chosen.

    `scripts/spike_retrieval.py` probed eight in-domain questions across three
    languages against six fluent out-of-domain ones and found NO single
    threshold that separates them: the shortest real query scores below the best
    impostor, because a one-word query has almost nothing to embed. What it did
    find is a higher bar that no out-of-domain probe reaches. Above it the
    vector half may answer alone; below it, it may only re-rank passages the
    lexical half has already vouched for.

    Absent the spike file the bar is None, and vectors admit nothing on their
    own. A fresh clone should refuse rather than inherit a number nobody has
    measured on its corpus.
    """
    f = RESULTS / "C2-retrieval.json"
    if not f.exists():
        return None
    return float(json.loads(f.read_text(encoding="utf-8"))["high_bar"])


def _content_terms(query: str) -> set[str]:
    return {t for t in _tokenise(query) if t not in STOPWORDS}


def _coverage(query_terms: set[str], text: str) -> int:
    return len(query_terms & set(_tokenise(text)))


def search(query: str, k: int = 5) -> list[dict]:
    passages, index = build()
    terms = _content_terms(query)
    lexical = index.get_scores(_tokenise(query))
    lexical_rank = {i: r for r, i in enumerate(np.argsort(-lexical), 1)}
    # Two content words are required once a query has three, and one before
    # that. The alternative — always requiring two — made "is detox allowed"
    # refuse while "detox" answered, and a retriever that gets WORSE as the user
    # explains themselves is not one anybody will use twice. A query that is
    # nothing but grammar has no content terms, so nothing votes and nothing is
    # returned.
    needed = MIN_TERMS_FOR_LEXICAL_VOTE if len(terms) >= 3 else 1
    votes_lexically = [
        bool(terms and lexical[i] > 0 and _coverage(terms, passages[i].text) >= needed)
        for i in range(len(passages))
    ]

    dense = _passage_vectors()
    dense_rank: dict[int, int] = {}
    dense_admits: set[int] = set()
    if dense is not None:
        e = vectors.embedder()
        try:
            sims = vectors.cosine(e.embed([query])[0], dense)
            dense_rank = {i: r for r, i in enumerate(np.argsort(-sims), 1)}
            bar = _vector_admission_bar()
            if bar is not None:
                dense_admits = {i for i in range(len(passages)) if sims[i] >= bar}
        except Exception:  # noqa: BLE001
            dense_rank = {}

    def fused(i: int) -> float:
        # A passage absent from one list contributes nothing from it, rather
        # than a penalty: RRF is a vote, and a retriever that did not rank
        # something has not voted against it.
        score = 0.0
        if votes_lexically[i]:
            score += 1.0 / (RRF_K + lexical_rank[i])
        if i in dense_rank:
            score += 1.0 / (RRF_K + dense_rank[i])
        return score

    # Cosine ranks EVERY passage, so "the vector half returned something" is not
    # evidence of anything. A passage enters the answer only if the lexical half
    # vouched for it or its similarity cleared the measured admission bar —
    # otherwise nothing is returned, which is the whole of the refusal contract.
    admitted = [i for i in range(len(passages)) if votes_lexically[i] or i in dense_admits]
    ranked = sorted(admitted, key=lambda i: (-fused(i), passages[i].id))[:k]

    out = []
    for rank, i in enumerate(ranked, 1):
        p = passages[i]
        out.append(
            {
                "rank": rank,
                "id": p.id,
                "score": round(fused(i), 5),
                "lexical_score": round(float(lexical[i]), 3),
                "matched_by": (
                    "both"
                    if votes_lexically[i] and i in dense_admits
                    else ("lexical" if votes_lexically[i] else "vector")
                ),
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
            f"{vectors.mode().capitalize()} retrieval over the project's own corpus — the "
            "brand kit, the dataset registry and the measured results. Admission is "
            "lexical; embeddings re-rank what the words already found, because the bar "
            "at which they could admit a passage on their own also admits questions this "
            "corpus cannot answer (docs/results/C2-retrieval.json). There is no "
            "generation step: an answer is the passages that matched, with their sources."
        )
        if hits
        else (
            "Nothing in the corpus matched. That is the correct answer to a question this "
            "project cannot cite, and it is returned rather than a plausible paragraph."
        ),
        "corpus_size": len(build()[0]),
    }
