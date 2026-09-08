"""Geometry checks on the deck, standing in for a visual pass.

LibreOffice is not installed on this machine, so the deck cannot be rasterised
and looked at here. Rather than declare it fine unseen, the defects a render
would catch first are checked arithmetically: nothing off the slide, nothing
overlapping, nothing crowding the edge, and no slide without its notes.

This is weaker than looking at it and is labelled as such. Anyone with
PowerPoint or LibreOffice should open the file once before it is submitted;
`docs/REDEPLOY_RUNBOOK.md` says so.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

pptx = pytest.importorskip("pptx", reason="python-pptx builds the deck")
from pptx import Presentation  # noqa: E402
from pptx.util import Inches  # noqa: E402

DECK = ROOT / "docs" / "artefacts" / "AI208_MAWSIM_deck.pptx"
MIN_MARGIN = Inches(0.5)


@pytest.fixture(scope="module")
def deck():
    if not DECK.exists():
        pytest.skip("run scripts/build_deck.py first")
    return Presentation(DECK)


def test_it_is_twelve_widescreen_slides(deck):
    assert len(deck.slides.__iter__.__self__._sldIdLst) == 12
    assert round(deck.slide_width / 914400, 2) == 13.33
    assert round(deck.slide_height / 914400, 2) == 7.5


def test_every_slide_carries_speaker_notes(deck):
    for i, slide in enumerate(deck.slides, 1):
        assert slide.has_notes_slide, f"slide {i} has no notes"
        text = slide.notes_slide.notes_text_frame.text.strip()
        assert len(text) > 120, f"slide {i}'s notes are too thin to deliver from: {text[:60]!r}"


def test_nothing_runs_off_the_slide(deck):
    """The single most common defect in a generated deck, and always visible."""
    bad = []
    for i, slide in enumerate(deck.slides, 1):
        for shape in slide.shapes:
            if shape.left is None or shape.width is None:
                continue
            if shape.left < 0 or shape.top < 0:
                bad.append(f"slide {i}: {shape.shape_type} starts off-slide")
            if shape.left + shape.width > deck.slide_width + Inches(0.02):
                bad.append(f"slide {i}: {shape.shape_type} runs past the right edge")
            if shape.top + shape.height > deck.slide_height + Inches(0.02):
                bad.append(f"slide {i}: {shape.shape_type} runs past the bottom")
    assert not bad, "\n".join(bad)


def test_nothing_crowds_the_edge(deck):
    bad = []
    for i, slide in enumerate(deck.slides, 1):
        for shape in slide.shapes:
            if shape.left is None:
                continue
            if shape.left < MIN_MARGIN - Inches(0.02):
                bad.append(f"slide {i}: a shape sits {shape.left / 914400:.2f}in from the left")
    assert not bad, "\n".join(bad)


def test_cards_and_charts_do_not_overlap(deck):
    """Text boxes may sit inside cards by design; solid shapes may not collide."""
    bad = []
    for i, slide in enumerate(deck.slides, 1):
        boxes = [
            (s.left, s.top, s.width, s.height, s.shape_type)
            for s in slide.shapes
            if s.left is not None and s.has_text_frame is False
        ]
        for a in range(len(boxes)):
            for b in range(a + 1, len(boxes)):
                ax, ay, aw, ah, at = boxes[a]
                bx, by, bw, bh, bt = boxes[b]
                if ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah:
                    bad.append(f"slide {i}: {at} overlaps {bt}")
    assert not bad, "\n".join(bad)


def test_the_numbers_on_the_slides_come_from_the_results(deck):
    """A deck that quotes a figure the results no longer contain is the exact
    drift the report and README are already guarded against."""
    import json

    red = json.loads((ROOT / "docs/results/E1-red-team.json").read_text())
    f = json.loads((ROOT / "docs/results/B1-forecast.json").read_text())
    text = " ".join(
        sh.text_frame.text for slide in deck.slides for sh in slide.shapes if sh.has_text_frame
    )
    assert f"{red['held']} of {red['cases']}" in text, "the red-team count on the slide has drifted"
    assert f"{f['weeks_won']} of {f['weeks_total']}" in text, "the forecast count has drifted"
