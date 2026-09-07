"""The guideline PDF must be reproducible, and must actually say the things
the rule set says.

A PDF that changes bytes on every build cannot be checked for currency: a
reviewer has no way to tell whether the file in the repository was generated
from the YAML beside it or from an older version of it.
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / "docs" / "brand" / "SIDRA-brand-guidelines.pdf"


def _build() -> bytes:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_brand_pdf.py")],
        check=True,
        capture_output=True,
        cwd=ROOT,
    )
    return PDF.read_bytes()


@pytest.fixture(scope="module")
def text() -> str:
    return "\n".join(p.extract_text() for p in PdfReader(str(PDF)).pages)


def test_the_pdf_is_reproducible():
    """Two builds, same bytes. reportlab stamps a creation date and a document
    id by default; rl_config.invariant is what turns both off."""
    first = hashlib.sha256(_build()).hexdigest()
    second = hashlib.sha256(_build()).hexdigest()
    assert first == second, "the PDF is not byte-identical across builds"


def test_the_committed_pdf_matches_the_current_yaml():
    """Catches a YAML edit committed without regenerating the document."""
    committed = PDF.read_bytes()
    assert hashlib.sha256(_build()).hexdigest() == hashlib.sha256(committed).hexdigest(), (
        "docs/brand/SIDRA-brand-guidelines.pdf is stale — "
        "run `uv run python scripts/build_brand_pdf.py`"
    )


def test_it_says_the_brand_is_fictional_on_the_cover(text: str):
    cover = PdfReader(str(PDF)).pages[0].extract_text()
    assert "fictional" in cover.lower()


def test_every_rule_appears_with_its_source(text: str):
    from services.api.brand import load_brand

    brand = load_brand()
    for rule in brand.claims_to_avoid:
        assert rule.id in text, f"{rule.id} is enforced but absent from the guidelines"
    cited = {brand.sources[r.source].code for r in brand.claims_to_avoid}
    for code in cited:
        assert code in text, f"source {code} is cited by a rule but not named in the PDF"


def test_unverified_clauses_are_marked_as_such(text: str):
    """A reader must be able to see which citations have been read verbatim."""
    from services.api.brand import load_brand

    brand = load_brand()
    if any(not r.clause_verified for r in brand.claims_to_avoid):
        assert "clause unverified" in text
