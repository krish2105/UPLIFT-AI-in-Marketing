"""Check a creative against the rules in the brand kit.

DETERMINISTIC ON PURPOSE
------------------------
A rule engine whose verdict depends on a model's mood cannot be audited, and the
claim this application makes is that every verdict cites the clause it came from.
So matching is regex over normalised text, the rules come from
`data/brand/sidra.yaml`, and the same creative gets the same verdict every time.

Phase C adds retrieval on top — pulling the clause text itself out of the corpus
so a reader can see the words rather than the reference. It does not move the
decision into a model.

THREE KINDS OF RULE
-------------------
  pattern      fires on a match. "sugar-free" is a nutrient-content claim.
  conditional  fires on a match UNLESS a qualifier is also present. "30% off" is
               fine with a period and a reference price and not otherwise, and a
               rule that flagged every discount would be switched off in a week.
  presence     fires on something MISSING. A creative naming pistachio knafeh
               without an allergen statement is a violation of absence, which no
               pattern can find.

FALSE POSITIVES ARE THE EXPENSIVE FAILURE
-----------------------------------------
A compliance tool that flags good copy gets ignored, and then it catches nothing
at all. `GOLD` below carries clean cases as well as violations, and precision is
reported next to recall.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from services.api.brand import Rule, load_brand
from services.api.creative.compose import Creative

#: Qualifiers that make a conditional rule acceptable.
QUALIFIERS: dict[str, tuple[str, ...]] = {
    # A discount claim needs a period and something to be discounted from.
    "SID-P-007": (
        r"\bwas\b.*\bnow\b",
        r"until\b",
        r"ends\b",
        r"\bfrom\s+AED",
        r"\d{1,2}\s*[–-]\s*\d{1,2}\s+\w+",
    ),
    # "fresh" and "artisan" are permitted where the piece says what makes it so.
    "SID-B-009": (
        r"baked (on site|this morning|today)",
        r"on site",
        r"in[- ]house",
        r"daily at \d",
    ),
    # A nutrition claim needs the accompanying declaration.
    "SID-N-011": (r"per 100\s*(ml|g)", r"nutrition(al)? information", r"per serving"),
}

#: Allergen statement patterns, in all three languages.
ALLERGEN_STATEMENT = re.compile(r"contains?\b|allergen|يحتوي|يحتوى|शामिल|एलर्जन", re.I)


def normalise(text: str) -> str:
    """Fold text so a rule cannot be evaded by punctuation or width.

    "sugar‑free" with a non-breaking hyphen and "ｓugar free" in full-width
    characters are both the same claim to a reader and neither matches a naive
    regex. NFKC folds the width; the hyphen class folds the rest.
    """
    t = unicodedata.normalize("NFKC", text)
    t = re.sub(r"[‐-―−]", "-", t)  # every dash to ASCII hyphen
    t = re.sub(r"[​-‏‪-‮]", "", t)  # zero-width and bidi marks
    return re.sub(r"\s+", " ", t).strip()


@dataclass(frozen=True)
class Finding:
    rule_id: str
    family: str
    severity: str
    verdict: str  # "fail"
    matched: list[str]
    why: str
    source_code: str
    source_title: str
    source_url: str
    clause: str
    clause_verified: bool
    clause_quote: str


@dataclass(frozen=True)
class Verdict:
    slot: str
    lang: str
    passed: bool
    findings: list[Finding] = field(default_factory=list)
    checked_rules: int = 0
    citations: int = 0


def _fires(rule: Rule, text: str, creative: Creative | None) -> tuple[bool, list[str]]:
    if rule.rule_type == "presence":
        return _presence_fires(rule, text, creative)

    hits = rule.hits(text)
    if not hits:
        return False, []

    if rule.rule_type == "conditional":
        for pattern in QUALIFIERS.get(rule.id, ()):
            if re.search(pattern, text, re.I):
                return False, []
    return True, hits


def _presence_fires(rule: Rule, text: str, creative: Creative | None) -> tuple[bool, list[str]]:
    """SID-A-006: a creative naming an allergen-bearing product must declare it."""
    if rule.id != "SID-A-006" or creative is None:
        return False, []
    brand = load_brand()
    try:
        product = brand.product(creative.product)
    except KeyError:
        return False, []
    if not product.allergens:
        return False, []
    if ALLERGEN_STATEMENT.search(text):
        return False, []
    return True, [
        f"{product.name} contains {', '.join(product.allergens)}; no statement in the copy"
    ]


def check(text: str, creative: Creative | None = None) -> Verdict:
    brand = load_brand()
    normalised = normalise(text)
    findings: list[Finding] = []

    for rule in brand.claims_to_avoid:
        fired, matched = _fires(rule, normalised, creative)
        if not fired:
            continue
        src = brand.sources[rule.source]
        findings.append(
            Finding(
                rule_id=rule.id,
                family=rule.family,
                severity=rule.severity,
                verdict="fail",
                matched=matched,
                why=rule.why.strip(),
                source_code=src.code,
                source_title=src.title,
                source_url=src.url,
                clause=rule.clause,
                clause_verified=rule.clause_verified,
                clause_quote=rule.clause_quote,
            )
        )

    return Verdict(
        slot=creative.slot if creative else "adhoc",
        lang=creative.lang if creative else "en",
        passed=not findings,
        findings=sorted(
            findings, key=lambda f: {"critical": 0, "high": 1, "medium": 2, "low": 3}[f.severity]
        ),
        checked_rules=len(brand.claims_to_avoid),
        citations=len(findings),
    )


# ── the gold set ────────────────────────────────────────────────────────────
#
# Forty cases: twenty that must fire and twenty that must not. Recall alone is
# easy to game — a rule that flags everything scores 1.0 — so precision is
# reported beside it and the clean half is deliberately adversarial, containing
# the words a naive matcher would trip on.

GOLD: list[tuple[str, str | None]] = [
    # ── must fire, with the rule that should catch it ──────────────────────
    ("Our new sugar-free date latte", "SID-N-001"),
    ("Zero sugar, all flavour", "SID-N-001"),
    ("A keto-friendly breakfast bake", "SID-N-002"),
    ("Low-carb and delicious", "SID-N-002"),
    ("The detox blend is back for summer", "SID-H-003"),
    ("Boost your immunity this winter", "SID-H-003"),
    ("Our superfood bowl", "SID-H-003"),
    ("Clinically proven to help you focus", "SID-H-004"),
    ("Treats fatigue in one cup", "SID-H-004"),
    ("Prevents the afternoon slump", "SID-H-004"),
    ("100% natural, chemical-free coffee", "SID-N-005"),
    ("All natural ingredients, always", "SID-N-005"),
    ("30% off this weekend", "SID-P-007"),
    ("Half price pastries", "SID-P-007"),
    ("Dubai's finest coffee", "SID-B-008"),
    ("The best knafeh in the city", "SID-B-008"),
    ("A world-class roast", "SID-B-008"),
    ("Artisan bakes, every day", "SID-B-009"),
    ("A blessed Ramadan offer", "SID-B-010"),
    ("Only 90 calories per cup", "SID-N-011"),
    # ── must NOT fire; several are deliberately near-misses ────────────────
    ("Cardamom cold brew, from 17:00. Marina Walk only.", None),
    ("Open at six, like always. Deira, from 06:00.", None),
    ("Pistachio knafeh is back. Contains pistachio, dairy and gluten.", None),
    ("Za'atar saj, baked on site each morning. Contains gluten and sesame.", None),
    ("Was AED 32, now AED 24. Until 30 September.", None),
    ("Freshly baked on site, daily at 06:00", None),
    ("Our date syrup latte is 26 dirhams", None),
    ("New hours at Al Barsha: 08:00 to 23:00", None),
    ("Two seats on the terrace, if the evening cools", None),
    ("A flat white and a saj before the market fills", None),
    ("We roast for iced service, not for espresso", None),
    ("The counter opens an hour earlier through Ramadan", None),
    ("Marina Walk has forty covers outdoors", None),
    ("Sidra means the tree that fruits in heat", None),
    ("Order ahead and collect at Downtown", None),
    ("Nutrition information per 100 ml is on the menu board: 90 calories", None),
    ("Our beans come from three farms in Yemen and Ethiopia", None),
    ("Closed for maintenance on Tuesday", None),
    ("Evening service now runs to one in the morning", None),
    ("A second knafeh for a friend, same price", None),
]

#: The rule set was written in English first and caught six violations in an
#: English creative, four in its Arabic translation and two in its Hindi one.
#: For a UAE brand that is a real gap rather than a cosmetic one, so these cases
#: exist to keep the three languages at parity. Reported separately, because a
#: single blended recall would hide exactly the imbalance they were added to fix.
GOLD_MULTILINGUAL: list[tuple[str, str, str | None]] = [
    ("ar", "لاتيه خالٍ من السكر", "SID-N-001"),
    ("ar", "مشروب ديتوكس يعزز المناعة", "SID-H-003"),
    ("ar", "يعالج التعب في كوب واحد", "SID-H-004"),
    ("ar", "طبيعي 100٪ بالكامل", "SID-N-005"),
    ("ar", "أفضل قهوة في دبي", "SID-B-008"),
    ("ar", "خصم هذا الأسبوع", "SID-P-007"),
    ("ar", "عرض مبارك في رمضان", "SID-B-010"),
    ("ar", "قهوة باردة بالهيل، من الساعة 5 مساءً. في مرسى دبي فقط.", None),
    ("ar", "نفتح السادسة صباحاً في ديرة", None),
    ("ar", "يحتوي على الفستق والحليب والغلوتين", None),
    ("hi", "शुगर-फ्री लाटे", "SID-N-001"),
    ("hi", "डिटॉक्स ड्रिंक जो इम्युनिटी बढ़ाए", "SID-H-003"),
    ("hi", "थकान का इलाज एक कप में", "SID-H-004"),
    ("hi", "100% प्राकृतिक सामग्री", "SID-N-005"),
    ("hi", "दुबई की बेहतरीन कॉफ़ी", "SID-B-008"),
    ("hi", "इस सप्ताहांत 30% की छूट", "SID-P-007"),
    ("hi", "इलायची कोल्ड ब्रू, शाम 5 बजे से। सिर्फ़ मरीना वॉक पर।", None),
    ("hi", "देरा में सुबह 6 बजे से खुला", None),
    ("hi", "इसमें पिस्ता, डेयरी और ग्लूटेन शामिल है", None),
    ("hi", "हमारी कॉफ़ी तीन खेतों से आती है", None),
]


def _score_cases(cases: list[tuple[str, str | None]]) -> dict:
    tp = fp = fn = tn = 0
    misses: list[dict] = []
    false_alarms: list[dict] = []
    for text, expected in cases:
        fired = {f.rule_id for f in check(text).findings}
        if expected is None:
            if fired:
                fp += 1
                false_alarms.append({"text": text, "fired": sorted(fired)})
            else:
                tn += 1
        elif expected in fired:
            tp += 1
        else:
            fn += 1
            misses.append({"text": text, "expected": expected, "fired": sorted(fired)})

    recall = tp / (tp + fn) if tp + fn else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    return {
        "cases": len(cases),
        "violations": tp + fn,
        "clean": tn + fp,
        "true_positives": tp,
        "false_negatives": fn,
        "false_positives": fp,
        "true_negatives": tn,
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "f1": round(2 * recall * precision / (recall + precision), 4)
        if recall + precision
        else 0.0,
        "missed": misses,
        "false_alarms": false_alarms,
    }


def evaluate_by_language() -> dict:
    """Recall and precision per language, never blended.

    A single number across all three would let strong English coverage hide weak
    Arabic coverage, which is precisely the failure these cases were written to
    stop."""
    out = {"en": _score_cases(GOLD)}
    for lang in ("ar", "hi"):
        out[lang] = _score_cases([(t, e) for lg, t, e in GOLD_MULTILINGUAL if lg == lang])
    out["worst_recall"] = min(v["recall"] for k, v in out.items() if k in ("en", "ar", "hi"))
    return out


def evaluate_gold() -> dict:
    """Recall, precision and the cases that were missed.

    Reported together because either alone is misleading: a rule that flags
    everything has perfect recall, and one that flags nothing has undefined
    precision and zero value.
    """
    tp = fp = fn = tn = 0
    misses: list[dict] = []
    false_alarms: list[dict] = []

    for text, expected in GOLD:
        v = check(text)
        fired = {f.rule_id for f in v.findings}
        if expected is None:
            if fired:
                fp += 1
                false_alarms.append({"text": text, "fired": sorted(fired)})
            else:
                tn += 1
        else:
            if expected in fired:
                tp += 1
            else:
                fn += 1
                misses.append({"text": text, "expected": expected, "fired": sorted(fired)})

    recall = tp / (tp + fn) if tp + fn else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0
    return {
        "cases": len(GOLD),
        "violations": tp + fn,
        "clean": tn + fp,
        "true_positives": tp,
        "false_negatives": fn,
        "false_positives": fp,
        "true_negatives": tn,
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "f1": round(2 * recall * precision / (recall + precision), 4)
        if recall + precision
        else 0.0,
        "missed": misses,
        "false_alarms": false_alarms,
    }
