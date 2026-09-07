"""The brand kit, loaded once and shared.

`data/brand/sidra.yaml` is the single source of truth for everything about
SIDRA: the Creative agent composes from it, the Compliance agent enforces its
rules, and the guideline PDF is generated from it. This module is the only
place that reads the file, so those three can never drift apart.

WHY THE RULES CARRY A `clause_verified` FLAG
--------------------------------------------
A compliance engine that cites a clause nobody has read is doing precisely what
this project argues against. So a rule records two different things: that the
SOURCE DOCUMENT was verified — code, title, revision, URL, all checked by
fetching it — and, separately, whether the specific CLAUSE has been read
verbatim. Phase C's corpus ingestion flips the second flag by supplying the
quote, and `test_a_verified_clause_carries_its_verbatim_quote` stops the flag
being set without one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BRAND_FILE = ROOT / "data" / "brand" / "sidra.yaml"


@dataclass(frozen=True)
class Zone:
    code: str
    name: str
    name_ar: str
    site: str
    lat: float
    lon: float
    seats: int
    outdoor_seats: int
    opens: str
    closes: str
    character: str
    demand_notes: str

    @property
    def outdoor_share(self) -> float:
        total = self.seats + self.outdoor_seats
        return self.outdoor_seats / total if total else 0.0


@dataclass(frozen=True)
class Product:
    id: str
    name: str
    name_ar: str
    price_aed: float
    dayparts: tuple[str, ...]
    allergens: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class Source:
    key: str
    code: str
    title: str
    publisher: str
    url: str
    verified: str
    revision: str | None = None

    def citation(self) -> str:
        """How this source is rendered wherever a rule is quoted."""
        rev = f" (rev. {self.revision})" if self.revision else ""
        return f"{self.code} {self.title}{rev} — {self.publisher}"


@dataclass(frozen=True)
class Rule:
    id: str
    family: str
    severity: str
    patterns: tuple[str, ...]
    why: str
    source: str
    clause: str
    clause_verified: bool
    clause_quote: str = ""
    #: "pattern" fires on a match; "presence" fires on something MISSING;
    #: "conditional" fires on a match unless a qualifier is also present.
    rule_type: str = "pattern"
    _compiled: tuple[re.Pattern[str], ...] = field(default=(), repr=False, compare=False)

    def matches(self, text: str) -> bool:
        """True when this rule fires on `text`.

        Presence rules never fire here: they are about something the copy does
        NOT contain, which needs the product context the Compliance agent has
        and a bare string does not.
        """
        if self.rule_type == "presence":
            return False
        return any(p.search(text) for p in self._compiled)

    def hits(self, text: str) -> list[str]:
        """The matched substrings, so a verdict can quote the copy it objected to."""
        return [m.group(0) for p in self._compiled for m in p.finditer(text)]


@dataclass(frozen=True)
class Brand:
    raw: dict
    zones: tuple[Zone, ...]
    products: tuple[Product, ...]
    sources: dict[str, Source]
    claims_to_avoid: tuple[Rule, ...]

    # ── identity ────────────────────────────────────────────────────────────
    @property
    def name(self) -> str:
        return self.raw["identity"]["name"]

    @property
    def name_ar(self) -> str:
        return self.raw["identity"]["name_ar"]

    @property
    def fictional(self) -> bool:
        return bool(self.raw["meta"]["fictional"])

    @property
    def disclaimer(self) -> str:
        return self.raw["meta"]["disclaimer"]

    @property
    def palette(self) -> dict[str, str]:
        return {k: v for k, v in self.raw["palette"].items() if k != "rules"}

    @property
    def voice(self) -> dict:
        return self.raw["voice"]

    # ── lookups ─────────────────────────────────────────────────────────────
    def zone(self, code: str) -> Zone:
        for z in self.zones:
            if z.code == code:
                return z
        raise KeyError(f"no zone {code!r}; have {[z.code for z in self.zones]}")

    def product(self, pid: str) -> Product:
        for p in self.products:
            if p.id == pid:
                return p
        raise KeyError(f"no product {pid!r}")

    def rule(self, rid: str) -> Rule:
        for r in self.claims_to_avoid:
            if r.id == rid:
                return r
        raise KeyError(f"no rule {rid!r}")

    def products_with_allergens(self) -> tuple[Product, ...]:
        return tuple(p for p in self.products if p.allergens)

    def contrast(self, a: str, b: str) -> float:
        """WCAG contrast between two named palette colours.

        The guidelines state a contrast rule in prose ("never place ink type on
        date"). Stating it is not enforcing it, so the number is available and a
        test asserts it.
        """
        return _contrast(self.palette[a], self.palette[b])


def _relative_luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    srgb = [int(h[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _contrast(a: str, b: str) -> float:
    la, lb = _relative_luminance(a), _relative_luminance(b)
    hi, lo = max(la, lb) + 0.05, min(la, lb) + 0.05
    return hi / lo


@lru_cache(maxsize=1)
def load_brand(path: Path | None = None) -> Brand:
    raw = yaml.safe_load((path or BRAND_FILE).read_text(encoding="utf-8"))

    zones = tuple(Zone(**z) for z in raw["zones"])
    products = tuple(
        Product(
            id=p["id"],
            name=p["name"],
            name_ar=p["name_ar"],
            price_aed=p["price_aed"],
            dayparts=tuple(p["dayparts"]),
            allergens=tuple(p.get("allergens", ())),
            notes=p.get("notes", ""),
        )
        for p in raw["products"]
    )
    sources = {
        key: Source(
            key=key,
            code=s["code"],
            title=s["title"],
            publisher=s["publisher"],
            url=s["url"],
            verified=str(s["verified"]),
            revision=str(s["revision"]) if s.get("revision") else None,
        )
        for key, s in raw["sources"].items()
    }
    rules = tuple(
        Rule(
            id=r["id"],
            family=r["family"],
            severity=r["severity"],
            patterns=tuple(r.get("patterns", ())),
            why=r["why"],
            source=r["source"],
            clause=r["clause"],
            clause_verified=bool(r.get("clause_verified", False)),
            clause_quote=r.get("clause_quote", ""),
            rule_type=r.get("rule_type", "pattern"),
            _compiled=tuple(re.compile(p, re.I) for p in r.get("patterns", ())),
        )
        for r in raw["claims_to_avoid"]
    )
    return Brand(raw=raw, zones=zones, products=products, sources=sources, claims_to_avoid=rules)
