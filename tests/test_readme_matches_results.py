"""The README's headline numbers, checked against the files that produced them.

The README is the first thing a reader sees and the last thing anybody
regenerates. Its claims table already carried "8/8 deployment checks" after the
suite had grown to ten — a number that was true when it was typed, stayed
plausible, and was wrong. `test_docs_match_results.py` guards docs/models.md
this way; this guards the front page.

Each entry names the claim, the result file, and how to derive the claimed value
from it. A number that is not derivable is not asserted here — the point is to
catch drift in numbers that HAVE a source, not to pretend every sentence has one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")


def result(name: str) -> dict:
    return json.loads((ROOT / "docs" / "results" / f"{name}.json").read_text(encoding="utf-8"))


CLAIMS = {
    "forecast win rate": (
        "B1-forecast",
        lambda r: f"{r['weeks_won']}/{r['weeks_total']} site-weeks",
    ),
    "uplift tolerance": ("B4-uplift", lambda r: f"{abs(r['worst_error_points']):.2f} pts"),
    "segment stability": ("B2-segments", lambda r: f"{r['bootstrap_stability']:.1%}"),
    "compliance recall": ("C1-compliance", lambda r: f"{r['worst_recall']:.0%}"),
    "red team": ("E1-red-team", lambda r: f"{r['held']} held"),
    "retrieval answered": (
        "C2-retrieval",
        lambda r: f"{r['end_to_end']['in_domain_answered']}/{r['end_to_end']['in_domain_total']}",
    ),
    "retrieval refused": (
        "C2-retrieval",
        lambda r: (
            f"{r['end_to_end']['out_of_domain_refused']}/{r['end_to_end']['out_of_domain_total']}"
        ),
    ),
    "deployment checks": ("A12-deploy", lambda r: f"{r['held']}/{r['total']} checks"),
    "contrast pairs": ("A2-contrast", lambda r: f"{r['pairs_measured']} pairs"),
    "red team attempts": ("E1-red-team", lambda r: f"{r['cases']} attacks"),
}


@pytest.mark.parametrize("claim", sorted(CLAIMS))
def test_the_readme_quotes_the_measurement(claim: str):
    name, derive = CLAIMS[claim]
    expected = derive(result(name))
    assert expected in README, (
        f"README does not contain {expected!r} for {claim}. "
        f"docs/results/{name}.json has moved and the front page has not."
    )


def test_the_live_urls_in_the_readme_are_the_ones_that_were_verified():
    """A README pointing at a URL nobody checked is a broken link with a citation."""
    deploy = result("A12-deploy")
    for url in (deploy["api"], deploy["web"]):
        assert url in README, f"{url} was verified but does not appear in the README"
