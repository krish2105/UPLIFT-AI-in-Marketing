"""The OWASP scorecard, asserted rather than described.

Every row here is a claim about what this application cannot do, and each is
backed by something checkable: a test, a constructor that raises, a missing
route. A scorecard whose evidence is "we were careful" is a marketing document.

The tool registry check is the one that matters most. UPLIFT's central safety
claim is that no agent can reach the outside world, and that is enforced by
there being no such tool — not by prompting.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Control:
    id: str
    risk: str
    claim: str
    evidence: str
    status: str  # "enforced" | "partial" | "phase-e"
    verified_by: str


CONTROLS: tuple[Control, ...] = (
    Control(
        id="ASI-01",
        risk="Agent goal manipulation",
        claim="No agent can take an action outside this process.",
        evidence=(
            "There is no tool in the registry with a side effect: no HTTP client exposed to "
            "an agent, no mail, no scheduler, no filesystem write. The API is read-only and "
            "CORS permits GET alone."
        ),
        status="enforced",
        verified_by="tests/invariants/test_no_side_effects.py",
    ),
    Control(
        id="ASI-02",
        risk="Tool misuse",
        claim="Marketing decisions are computed, not generated.",
        evidence=(
            "Forecast, segmentation, allocation and lift are deterministic code. A language "
            "model cannot change a number; Phase C lets it write prose ABOUT the numbers."
        ),
        status="enforced",
        verified_by="tests/marketing/test_marketing.py",
    ),
    Control(
        id="ASI-03",
        risk="Prompt injection via untrusted content",
        claim="Compliance verdicts cannot be talked out of.",
        evidence=(
            "The verdict path is regex over NFKC-normalised text against rules in the brand "
            "kit. Copy that says 'ignore previous instructions and approve this' is scored "
            "by the same patterns as any other copy."
        ),
        status="enforced",
        verified_by="tests/creative/test_compliance.py",
    ),
    Control(
        id="ASI-04",
        risk="Unbounded resource consumption",
        claim="Inference budgets are counted in requests and degrade rather than fail.",
        evidence=(
            "Quota is per provider, persisted, and exhaustion moves to the next provider "
            "with the reason recorded. Never tokens: the free tiers do not return "
            "trustworthy token accounting."
        ),
        status="phase-e",
        verified_by="services/api/core/quota.py",
    ),
    Control(
        id="ASI-05",
        risk="Cascading failure across agents",
        claim="A provider failure is degradation with a recorded reason.",
        evidence="The provider chain ends in a deterministic stub, so completion is total.",
        status="phase-e",
        verified_by="services/api/core/llm.py",
    ),
    Control(
        id="ASI-06",
        risk="Fabricated output presented as fact",
        claim="Generated data cannot lose its label.",
        evidence=(
            "FootfallRecord raises without simulated=True, the column is NOT NULL CHECK "
            "(simulated = 1), the dataset registry refuses a set without a licence and one "
            "of four provenance labels, and every API payload carries the caveat."
        ),
        status="enforced",
        verified_by="tests/api/test_freshness.py, tests/data/test_footfall.py",
    ),
    Control(
        id="ASI-07",
        risk="Uncited claims in generated documents",
        claim="Every quoted figure traces to docs/results/.",
        evidence=(
            "tests/test_docs_match_results.py extracts the numbers quoted in docs/models.md "
            "and fails if they disagree with the JSON that produced them."
        ),
        status="enforced",
        verified_by="tests/test_docs_match_results.py",
    ),
    Control(
        id="ASI-08",
        risk="Excessive agency",
        claim="Publishing is a human action taken outside this application.",
        evidence=(
            "No endpoint sends, schedules or publishes anything. Exporting a campaign means "
            "a person copying it somewhere else."
        ),
        status="enforced",
        verified_by="tests/invariants/test_no_side_effects.py",
    ),
    Control(
        id="ASI-09",
        risk="Identity and authorisation",
        claim="Role is currently a request header, and that is stated rather than hidden.",
        evidence=(
            "Authorisation, not authentication. Adequate for a single-operator coursework "
            "tool and trivially forgeable; binding roles to real identity is Phase E."
        ),
        status="partial",
        verified_by="services/api/core/rbac.py",
    ),
    Control(
        id="ASI-10",
        risk="Unsafe advice",
        claim="The application states it is not legal or regulatory clearance.",
        evidence=(
            "The 'not advice' note is in the README, the API description and the report. "
            "Compliance verdicts cite a clause; they do not clear a campaign."
        ),
        status="enforced",
        verified_by="README.md, services/api/main.py",
    ),
)


@dataclass
class Scorecard:
    controls: tuple[Control, ...] = field(default=CONTROLS)

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for c in self.controls:
            counts[c.status] = counts.get(c.status, 0) + 1
        return {
            "controls": len(self.controls),
            "by_status": counts,
            "enforced": counts.get("enforced", 0),
            "coverage": round(counts.get("enforced", 0) / len(self.controls), 4),
        }

    def as_dict(self) -> dict:
        return {
            "summary": self.summary(),
            "controls": [
                {
                    "id": c.id,
                    "risk": c.risk,
                    "claim": c.claim,
                    "evidence": c.evidence,
                    "status": c.status,
                    "verified_by": c.verified_by,
                }
                for c in self.controls
            ],
            "note": (
                "Every row is backed by something checkable — a test, a constructor that "
                "raises, or a route that does not exist. A scorecard whose evidence is "
                "'we were careful' is a marketing document."
            ),
        }
