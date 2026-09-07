"""A persona panel that scores creatives — and says what it is not.

WHAT THIS IS
------------
Five personas, each a stated set of priorities, scoring a creative on four
criteria. The scoring is DETERMINISTIC: the same creative gets the same score
every time, which is the only way a panel score can be compared across variants
or used by a planner.

WHAT THIS IS NOT, AND THE APPLICATION SAYS SO EVERY TIME IT SHOWS A SCORE
------------------------------------------------------------------------
It is not customer research. It does not observe a reaction; it applies a rule
set someone wrote down. Its value is as a fast, consistent FILTER — catching the
variant that ignores the daypart it is booked into, or that buries the offer —
before a human spends attention on it. Treating it as evidence about real
customers would be the single worst misuse of this application, so every
persona publishes what it over- and under-weights, and the panel reports its
spread as well as its mean.

Phase C lets a language model write the persona's REASONING. The score stays
here, in code, for the reason above.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from services.api.creative.compose import Creative

CRITERIA = ("clarity", "specificity", "fit_to_daypart", "brand_voice")


@dataclass(frozen=True)
class Persona:
    id: str
    name: str
    stance: str
    #: What this persona weights, per criterion. They sum to 1.
    weights: dict[str, float]
    over_weights: str
    under_weights: str
    prefers_daypart: str | None = None


PANEL: tuple[Persona, ...] = (
    Persona(
        id="commuter",
        name="The 07:00 commuter",
        stance="Buys the same thing every weekday and will not read a second line.",
        weights={"clarity": 0.45, "specificity": 0.30, "fit_to_daypart": 0.20, "brand_voice": 0.05},
        over_weights="Speed and legibility. Rates a short line highly even when it says little.",
        under_weights="Tone. Would not notice a voice breach that a brand manager would.",
        prefers_daypart="morning",
    ),
    Persona(
        id="resident",
        name="The Al Barsha regular",
        stance="Comes with family at the weekend and plans around opening hours.",
        weights={"clarity": 0.25, "specificity": 0.40, "fit_to_daypart": 0.15, "brand_voice": 0.20},
        over_weights="Concrete times, sites and prices. Penalises anything vague.",
        under_weights="Novelty. Rates a familiar offer as highly as a new one.",
        prefers_daypart="midday",
    ),
    Persona(
        id="marina_evening",
        name="The Marina evening table",
        stance="Decides at 18:00 whether to sit outside, and checks the weather first.",
        weights={"clarity": 0.20, "specificity": 0.30, "fit_to_daypart": 0.35, "brand_voice": 0.15},
        over_weights="Anything about the evening or the terrace.",
        under_weights="Morning offers, which it scores near zero regardless of quality.",
        prefers_daypart="evening",
    ),
    Persona(
        id="value",
        name="The Deira value shopper",
        stance="Price-led, early, and sceptical of an offer that does not state its terms.",
        weights={"clarity": 0.30, "specificity": 0.45, "fit_to_daypart": 0.10, "brand_voice": 0.15},
        over_weights="Stated prices and stated end dates.",
        under_weights="Atmosphere. A well-written line with no number in it scores poorly.",
        prefers_daypart="morning",
    ),
    Persona(
        id="brand_manager",
        name="The brand manager",
        stance="Not a customer. Reads for voice breaches and for claims that will need defending.",
        weights={"clarity": 0.15, "specificity": 0.20, "fit_to_daypart": 0.10, "brand_voice": 0.55},
        over_weights="Voice rules, to the point of penalising copy customers would like.",
        under_weights="Whether anyone would actually buy anything.",
        prefers_daypart=None,
    ),
)

#: Signals scored per criterion. Each is a regex and a contribution; the score
#: is the clipped sum. Written out rather than learned, because a panel whose
#: rubric cannot be read is not a rubric.
SIGNALS: dict[str, list[tuple[str, float]]] = {
    "clarity": [
        (r"^.{0,45}$", 2.0),  # a headline that fits in a glance
        (r"\b(only|just)\b", 0.5),
        (r"[;:]|\band\b.*\band\b", -1.5),  # more than one idea
        (r"\b(experience|journey|elevate|curated)\b", -2.0),
    ],
    "specificity": [
        (r"\b\d{1,2}:\d{2}\b", 2.5),  # an exact time
        (r"\bAED\s?\d+|\b\d+\s?(dirhams|AED)\b", 2.0),
        (r"\b(Marina Walk|Deira|Downtown|Al Barsha)\b", 2.0),
        (r"\b(until|ends|from)\b\s+\d", 1.5),
        (r"\b(soon|now available|coming|discover)\b", -2.0),
    ],
    "fit_to_daypart": [
        (r"\b(morning|06:00|07:00|08:00|breakfast|before)\b", 0.0),
        (r"\b(evening|17:00|18:00|night|after dark|terrace)\b", 0.0),
    ],
    "brand_voice": [
        (r"\b(best|finest|world[- ]class|number one)\b", -3.0),
        (r"\b(blessed|holy|sacred)\b", -3.0),
        (r"\b(artisan|handcrafted|authentic)\b", -1.5),
        (r"\b(sugar[- ]free|detox|immunity|clinically|100% natural)\b", -4.0),
        (r"\b(cardamom|pistachio|za'atar|saj|knafeh|date syrup)\b", 1.5),  # names the product
        (r"^[A-Z][^A-Z]*$", 0.5),  # sentence case
    ],
}


def _criterion_score(criterion: str, creative: Creative) -> float:
    """0-10 on one criterion."""
    text = creative.text
    if criterion == "fit_to_daypart":
        # Scored against the slot the creative is actually booked into.
        morning = bool(re.search(SIGNALS[criterion][0][0], text, re.I))
        evening = bool(re.search(SIGNALS[criterion][1][0], text, re.I))
        wanted = creative.daypart
        if wanted == "morning":
            return 8.5 if morning else (3.0 if evening else 5.0)
        if wanted == "evening":
            return 8.5 if evening else (3.0 if morning else 5.0)
        return 6.0 if not (morning or evening) else 5.0

    score = 5.0
    for pattern, delta in SIGNALS[criterion]:
        if re.search(pattern, text, re.I | re.M):
            score += delta
    return max(0.0, min(10.0, score))


@dataclass(frozen=True)
class PersonaScore:
    persona: str
    name: str
    total: float
    criteria: dict[str, float]
    note: str


@dataclass(frozen=True)
class PanelResult:
    slot: str
    lang: str
    mean: float
    spread: float
    scores: list[PersonaScore]
    simulated: bool = True


def score(creative: Creative) -> PanelResult:
    criteria = {c: _criterion_score(c, creative) for c in CRITERIA}
    scores: list[PersonaScore] = []

    for p in PANEL:
        adjusted = dict(criteria)
        # A persona whose daypart the creative is not booked into discounts it,
        # which is the panel's most useful single behaviour: it catches a good
        # ad pointed at the wrong hour.
        if p.prefers_daypart and p.prefers_daypart != creative.daypart:
            adjusted["fit_to_daypart"] = max(0.0, adjusted["fit_to_daypart"] - 3.0)
        total = sum(adjusted[c] * p.weights[c] for c in CRITERIA)
        scores.append(
            PersonaScore(
                persona=p.id,
                name=p.name,
                total=round(total, 2),
                criteria={k: round(v, 2) for k, v in adjusted.items()},
                note=p.stance,
            )
        )

    totals = [s.total for s in scores]
    mean = sum(totals) / len(totals)
    spread = max(totals) - min(totals)
    return PanelResult(
        slot=creative.slot,
        lang=creative.lang,
        mean=round(mean, 2),
        spread=round(spread, 2),
        scores=sorted(scores, key=lambda s: -s.total),
    )
