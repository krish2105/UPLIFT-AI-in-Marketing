"""Retrieval, and the two ways it is allowed to fail.

The contract is narrow and worth stating: an answer is passages that matched,
with their sources, and NOTHING is returned when nothing matched. Both halves of
that are testable without a model, and the no-model case is the one that runs in
CI — so these tests force the embedder off and assert the floor still holds.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))

from services.api.rag import corpus, vectors  # noqa: E402


@pytest.fixture
def lexical_only(monkeypatch):
    """No embedder, which is what a free instance actually has.

    The whole suite must pass with no model and no network, so this is the
    default condition rather than an edge case.
    """
    corpus._passage_vectors.cache_clear()
    vectors.embedder.cache_clear()
    monkeypatch.setattr(vectors, "embedder", lambda: None)
    monkeypatch.setattr(corpus, "_passage_vectors", lambda: None)
    # No teardown: monkeypatch restores both names, and the real caches were
    # never populated while they were patched out. Clearing them here would run
    # BEFORE that restore and hit the lambdas, which have no cache to clear —
    # which is exactly what it did on the first run.


ANSWERABLE = ["sugar-free claim rule", "detox", "is detox allowed", "does weather affect demand"]

# Fluent, plausible, and aimed at exactly this kind of tool — which is what a
# confused user types, rather than keyboard mash.
UNANSWERABLE = [
    "what is the capital of Peru",
    "how do I reset my password",
    "send me the invoice",
    "when is the next board meeting",
    "what were quarterly earnings per share",
]


@pytest.mark.parametrize("query", ANSWERABLE)
def test_a_question_the_corpus_can_answer_is_answered(lexical_only, query):
    hits = corpus.search(query, 3)
    assert hits, f"{query!r} returned nothing"
    assert all(h["source_url"] for h in hits), "a citation without a source is not a citation"


@pytest.mark.parametrize("query", UNANSWERABLE)
def test_a_question_the_corpus_cannot_answer_is_refused(lexical_only, query):
    assert corpus.answer(query)["answered"] is False, (
        f"{query!r} was answered; refusing is the contract"
    )


def test_explaining_yourself_does_not_break_the_query(lexical_only):
    """A retriever that gets worse as the user adds words is not usable.

    An earlier coverage rule required two matching content words unconditionally,
    so "detox" answered and "is detox allowed" refused.
    """
    assert corpus.search("detox", 3), "the one-word case"
    assert corpus.search("is detox allowed", 3), "the same question, spelled out"


def test_grammar_alone_is_not_evidence(lexical_only):
    """The bug this guards is subtle: a stopword that is common in its language
    and rare in THIS corpus gets a high IDF and reads as distinctive. It arrived
    first as Hindi `करता` and then as English `this`."""
    assert corpus.answer("what is that")["answered"] is False
    assert corpus.answer("how do they do it")["answered"] is False


def test_vectors_cannot_admit_a_passage_on_their_own():
    """The admission bar is not a tuning knob; it comes from a measurement.

    If C2-retrieval.json ever reports that a single threshold separates
    in-domain from out-of-domain, this test should be revisited deliberately
    rather than silently satisfied.
    """
    spike = json.loads((ROOT / "docs" / "results" / "C2-retrieval.json").read_text())
    assert spike["separable_by_a_single_threshold"] is False
    assert spike["high_bar"] > max(x["max"] for x in spike["out_of_domain"])
    cleared = [x for x in spike["in_domain"] if x["max"] >= spike["high_bar"]]
    assert len(cleared) <= 1, "the bar has drifted low enough for vectors to answer alone"


def test_the_bar_is_read_from_the_measurement_not_hardcoded():
    spike = json.loads((ROOT / "docs" / "results" / "C2-retrieval.json").read_text())
    corpus._vector_admission_bar.cache_clear()
    assert corpus._vector_admission_bar() == pytest.approx(spike["high_bar"])


def test_retrieval_mode_is_reported(lexical_only):
    """A reader must not have to infer the mode from answer quality."""
    assert vectors.describe()["retrieval"] == "lexical"
    assert vectors.describe()["embedder"] is None
