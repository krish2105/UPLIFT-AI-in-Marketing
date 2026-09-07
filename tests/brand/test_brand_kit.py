"""The brand kit is a contract, not a document.

Every downstream component reads `data/brand/sidra.yaml`: the Creative agent
composes from it, the Compliance agent enforces its rules, and the guideline
PDF is generated from it. So the things that would silently break those
components are asserted here rather than reviewed by eye.
"""

from __future__ import annotations

import re

import pytest

from services.api.brand import Brand, load_brand


@pytest.fixture(scope="module")
def brand() -> Brand:
    return load_brand()


def test_the_brand_declares_itself_fictional(brand: Brand):
    """A reader must not be able to reach any brand fact without this."""
    assert brand.fictional is True
    assert "fictional" in brand.disclaimer.lower()
    assert "simulated" in brand.disclaimer.lower()


def test_four_zones_with_coordinates_inside_dubai(brand: Brand):
    assert len(brand.zones) == 4
    assert {z.code for z in brand.zones} == {"DXB-DTN", "DXB-MOE", "DXB-MAR", "DXB-DEI"}
    for z in brand.zones:
        # Dubai's bounding box. A transposed lat/lon is the classic geocoding
        # bug and it would silently corrupt every event-distance feature.
        assert 24.7 < z.lat < 25.4, f"{z.code} latitude outside Dubai"
        assert 54.8 < z.lon < 55.6, f"{z.code} longitude outside Dubai"


def test_marina_is_the_outdoor_site(brand: Brand):
    """The forecast's whole per-zone argument rests on this being true."""
    marina = brand.zone("DXB-MAR")
    moe = brand.zone("DXB-MOE")
    assert marina.outdoor_seats > marina.seats * 0.5
    assert moe.outdoor_seats == 0


def test_every_rule_names_a_source_that_exists(brand: Brand):
    """A rule citing a source the kit does not define cannot be checked."""
    for rule in brand.claims_to_avoid:
        assert rule.source in brand.sources, f"{rule.id} cites unknown source {rule.source!r}"
        src = brand.sources[rule.source]
        assert src.url, f"{rule.id} source {rule.source} has no URL"
        assert src.title, f"{rule.id} source {rule.source} has no title"
        assert rule.clause, f"{rule.id} names no clause"


def test_a_verified_clause_carries_its_verbatim_quote(brand: Brand):
    """This is the honesty gate.

    `clause_verified: true` is a claim that someone read the clause. It is only
    allowed to be true when the quote is present, so the flag cannot drift into
    meaning "probably right".
    """
    for rule in brand.claims_to_avoid:
        if rule.clause_verified:
            assert rule.clause_quote, f"{rule.id} claims a verified clause with no quote"
            assert len(rule.clause_quote.strip()) > 20, f"{rule.id} quote is too short to be one"


def test_unverified_clauses_are_only_external_documents(brand: Brand):
    """SIDRA's own guidelines are written here, so their clauses are verifiable
    immediately. Anything still unverified must be an external document awaiting
    Phase C's corpus ingestion."""
    for rule in brand.claims_to_avoid:
        if not rule.clause_verified:
            assert rule.source != "sidra-brand", (
                f"{rule.id} cites SIDRA's own guidelines but is unverified — "
                "the quote is in this repository"
            )


def test_every_pattern_compiles(brand: Brand):
    """A rule whose regex does not compile silently never fires."""
    for rule in brand.claims_to_avoid:
        for pattern in rule.patterns:
            re.compile(pattern, re.I)


def test_rules_actually_catch_what_they_describe(brand: Brand):
    """Spot-check the rule set against copy it must reject.

    Written as (text, expected rule id) so a pattern edit that stops matching
    fails here rather than in a compliance report.
    """
    cases = [
        ("Our sugar-free date latte", "SID-N-001"),
        ("A keto-friendly bake", "SID-N-002"),
        ("The immunity blend is back", "SID-H-003"),
        ("Clinically proven to help", "SID-H-004"),
        ("100% natural ingredients", "SID-N-005"),
        ("30% off this weekend", "SID-P-007"),
        ("Dubai's finest coffee", "SID-B-008"),
        ("Freshly baked every day", "SID-B-009"),
    ]
    for text, expected in cases:
        hits = {r.id for r in brand.claims_to_avoid if r.matches(text)}
        assert expected in hits, f"{expected} did not fire on {text!r}; fired: {sorted(hits)}"


def test_compliant_copy_is_not_flagged(brand: Brand):
    """False positives are the expensive failure: a compliance tool that flags
    good copy gets switched off."""
    clean = [
        "Cardamom cold brew, from 17:00. Marina Walk only.",
        "Pistachio knafeh is back at Deira. Contains pistachio, dairy and gluten.",
        "Open from 06:00 at Al Rigga.",
    ]
    for text in clean:
        hits = {r.id for r in brand.claims_to_avoid if r.matches(text)}
        assert not hits, f"clean copy flagged by {sorted(hits)}: {text!r}"


def test_products_with_allergens_declare_them(brand: Brand):
    """SID-A-006 checks creatives for an allergen statement. That rule is only
    meaningful if the product data says which products carry one."""
    knafeh = brand.product("pistachio-knafeh")
    assert "pistachio" in knafeh.allergens
    assert brand.products_with_allergens(), "no product declares an allergen"


def test_the_palette_never_asks_for_unreadable_type(brand: Brand):
    """The brand palette is used to compose creatives, so its own contrast rule
    has to hold or the Creative agent will emit unreadable ads."""
    assert brand.contrast("ink", "semolina") >= 4.5
    assert brand.contrast("semolina", "date") >= 4.5
    # The rule the guidelines state in prose, asserted numerically.
    assert brand.contrast("ink", "date") < 4.5, (
        "the guidelines say ink on date fails; if it now passes, fix the guidelines"
    )


def test_no_orphan_sources(brand: Brand):
    """A source no rule cites is dead data.

    It also never reaches the generated PDF, so it looks like part of the
    evidence base while being invisible to any reader. This test found exactly
    that: CXG 2-1985 sat in the kit uncited until SID-N-011 was written.
    """
    cited = {r.source for r in brand.claims_to_avoid}
    orphans = set(brand.sources) - cited
    assert not orphans, f"sources defined but never cited by a rule: {sorted(orphans)}"


def test_the_nutrient_declaration_rule_fires(brand: Brand):
    assert brand.rule("SID-N-011").matches("Only 90 calories")
    assert brand.rule("SID-N-011").matches("12g protein in every cup")
