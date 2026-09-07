"""The Term 4 artefacts are regenerated, never edited.

A deck that says "36 of 36 site-weeks" is only worth reading if it still says
that after the evaluation is re-run. The temptation with a deliverable is to fix
a sentence by hand in the .md — and from that moment the document and the
results disagree, plausibly and invisibly.

So every artefact is compared against what its builder produces right now. If
they differ, the artefact was hand-edited or the numbers moved, and either way
the fix is to run the builder rather than to adjust the test.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))

from scripts.build_report import (  # noqa: E402
    ARTEFACTS,
    REQUIRED,
    RESULTS,
    MissingResult,
    build_deck,
    build_demo,
    build_markdown,
    build_notebook,
    build_viva,
)

# The report stamps the day it was generated; nothing else does. Normalise that
# one line rather than exempting the whole document from the check.
DATED = re.compile(r"^Generated \d{4}-\d{2}-\d{2} from", re.MULTILINE)


def _normalise(text: str) -> str:
    return DATED.sub("Generated <date> from", text)


@pytest.mark.parametrize(
    ("filename", "builder"),
    [
        ("AI208_MAWSIM_report.md", build_markdown),
        ("AI208_deck_outline.md", build_deck),
        ("AI208_viva_15.md", build_viva),
        ("AI208_demo_3min.md", build_demo),
        ("AI208_MAWSIM_notebook.ipynb", build_notebook),
    ],
)
def test_artefact_matches_its_builder(filename: str, builder):
    path = ARTEFACTS / filename
    assert path.exists(), f"{filename} is missing; run scripts/build_report.py"
    assert _normalise(path.read_text(encoding="utf-8")) == _normalise(builder()), (
        f"{filename} differs from what its builder produces. "
        "Run `uv run python scripts/build_report.py` — do not edit the artefact."
    )


def test_every_required_result_exists():
    missing = [name for name in REQUIRED if not (RESULTS / f"{name}.json").exists()]
    assert not missing, f"missing results: {missing}"


def test_a_builder_refuses_rather_than_omitting(tmp_path, monkeypatch):
    """The failure mode worth designing for is a section that quietly disappears.

    If a result is absent the builder must raise, because a report missing its
    compliance section reads exactly like a report whose compliance section had
    nothing to say."""
    import scripts.build_report as br

    monkeypatch.setattr(br, "RESULTS", tmp_path)
    with pytest.raises(MissingResult):
        br.build_deck()


def test_notebook_is_valid_and_its_code_compiles():
    nb = json.loads((ARTEFACTS / "AI208_MAWSIM_notebook.ipynb").read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    assert len(code) >= 5, "the notebook should reproduce more than a token number"
    for i, cell in enumerate(code):
        compile("".join(cell["source"]), f"notebook-cell-{i}", "exec")
