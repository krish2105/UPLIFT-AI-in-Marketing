"""Every number in a published document traces to docs/results/.

This is the mechanism behind the claim, not a restatement of it. The rule is
easy to state and easy to break silently: a script's output changes, and the
prose that quoted it a month ago keeps the old figure and still reads
plausibly. So the numbers quoted in docs/models.md are extracted and compared
against the JSON that produced them.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPIKE = json.loads((ROOT / "docs" / "results" / "A9-embedding-spike.json").read_text())
MODELS_MD = (ROOT / "docs" / "models.md").read_text(encoding="utf-8")


def _candidate(name_fragment: str) -> dict:
    for c in SPIKE["candidates"]:
        if name_fragment in c["name"]:
            return c
    raise KeyError(name_fragment)


def _in_doc(value: float) -> bool:
    """True when the value appears in the document at three decimal places,
    with either sign convention the prose might use."""
    for text in (f"{value:+.3f}", f"{abs(value):.3f}"):
        if text.replace("-", "−") in MODELS_MD or text in MODELS_MD:
            return True
    return False


@pytest.mark.parametrize(
    "fragment", ["bge-m3", "nomic-embed-text", "MiniLM-L12-v2", "mpnet-base-v2"]
)
def test_every_quoted_margin_matches_the_spike(fragment: str):
    c = _candidate(fragment)
    if not c.get("available"):
        pytest.skip(f"{fragment} was not measured on this machine")
    assert _in_doc(c["worst_margin_hi"]), (
        f"{c['name']} HI margin {c['worst_margin_hi']} not in models.md"
    )
    assert _in_doc(c["worst_margin_ar"]), (
        f"{c['name']} AR margin {c['worst_margin_ar']} not in models.md"
    )


@pytest.mark.parametrize(
    "fragment", ["bge-m3", "nomic-embed-text", "MiniLM-L12-v2", "mpnet-base-v2"]
)
def test_every_quoted_dimension_matches_the_spike(fragment: str):
    c = _candidate(fragment)
    if not c.get("available"):
        pytest.skip(f"{fragment} was not measured on this machine")
    assert re.search(rf"\|\s*{c['dim']}\s*\|", MODELS_MD), f"dim {c['dim']} not in the table"


def test_the_decision_recorded_in_the_document_is_the_measured_one():
    assert SPIKE["decision"]["local"] == "bge-m3:567m"
    assert "bge-m3:567m" in MODELS_MD
    deployed = SPIKE["decision"]["deployed"]
    assert deployed and deployed.split("/")[-1] in MODELS_MD


def test_the_disqualification_is_real_and_stays_real():
    """nomic-embed-text ranks an unrelated sentence above the correct
    translation. If it ever clears the bar the page needs rewriting, not
    silently updating — so this asserts the failure, not the pass."""
    c = _candidate("nomic-embed-text")
    if not c.get("available"):
        pytest.skip("nomic-embed-text not installed")
    assert not c["clears_bar"]
    assert c["worst_margin_hi"] < 0 or c["worst_margin_ar"] < 0
    assert c["name"] in SPIKE["decision"]["disqualified"]
    assert "disqualified" in MODELS_MD.lower()


def test_the_concrete_failure_numbers_are_quoted_correctly():
    """models.md claims nomic scores the depreciation control at 0.528 against
    0.452 and 0.401 for the translations. Those three numbers are the argument."""
    c = _candidate("nomic-embed-text")
    if not c.get("available"):
        pytest.skip("nomic-embed-text not installed")
    probe = next(p for p in c["probes"] if p["probe"] == "nutrition-claim")
    for value in (probe["hardest_control"], probe["en_hi"], probe["en_ar"]):
        assert f"{value:.3f}" in MODELS_MD, f"{value} is quoted in prose but not measured"


def test_the_margin_bar_quoted_matches_the_script():
    assert f"{SPIKE['margin_bar']}" in MODELS_MD
