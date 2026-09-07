"""Compliance and panel results, written where a document can cite them."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

from pipeline.common import now_iso  # noqa: E402
from services.api.creative import compliance, panel  # noqa: E402
from services.api.creative.compose import all_creatives  # noqa: E402

RESULTS = ROOT / "docs" / "results"
RECALL_TARGET = 0.90


def main() -> int:
    by_lang = compliance.evaluate_by_language()
    overall = compliance.evaluate_gold()

    creatives = all_creatives()
    verdicts = []
    for c in creatives:
        v = compliance.check(c.text, c)
        p = panel.score(c)
        verdicts.append(
            {
                "slot": c.slot,
                "lang": c.lang,
                "seed": c.seed,
                "passed": v.passed,
                "findings": [f.rule_id for f in v.findings],
                "panel_mean": p.mean,
                "panel_spread": p.spread,
            }
        )

    payload = {
        "task": "C1-compliance",
        "generated_by": "scripts/run_phase_c.py",
        "generated_at": now_iso(),
        "method": (
            "Regex over NFKC-normalised text against the eleven rules in "
            "data/brand/sidra.yaml. Deterministic: a rule engine whose verdict depends "
            "on a model's mood cannot be audited. Three rule types — pattern, "
            "conditional (fires unless a qualifier is present) and presence (fires on "
            "something missing, such as an allergen statement)."
        ),
        "target_recall": RECALL_TARGET,
        "by_language": {k: v for k, v in by_lang.items() if k in ("en", "ar", "hi")},
        "worst_recall": by_lang["worst_recall"],
        "meets_target": by_lang["worst_recall"] >= RECALL_TARGET,
        "overall_english": {k: overall[k] for k in ("cases", "recall", "precision", "f1")},
        "note_on_language": (
            "Recall is reported per language and never blended. The rule set was "
            "written in English first and on the same violating creative caught six "
            "rules in English, four in Arabic and two in Hindi — for a UAE brand a real "
            "gap rather than a cosmetic one. Arabic and Hindi patterns were added and "
            "the gold set extended; a single blended number would have hidden the "
            "imbalance it was written to find."
        ),
        "note_on_precision": (
            "Precision is reported beside recall because a rule that flags everything "
            "scores perfect recall. The clean half of the gold set is deliberately "
            "adversarial: it contains discounts with stated terms, allergen statements, "
            "and the word 'fresh' qualified by 'baked on site'."
        ),
        "creatives": verdicts,
        "panel_is_not_research": (
            "Panel scores are a deterministic rubric applied by five stated personas. "
            "They are a filter, not evidence about real customers, and every persona "
            "publishes what it over- and under-weights."
        ),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "C1-compliance.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    for lang in ("en", "ar", "hi"):
        v = by_lang[lang]
        print(
            f"  {lang}  {v['cases']:>2} cases  recall {v['recall']:.0%}  precision {v['precision']:.0%}"
        )
    print(
        f"\nworst recall {by_lang['worst_recall']:.0%} (target {RECALL_TARGET:.0%}) "
        f"{'PASS' if payload['meets_target'] else 'FAIL'}"
    )
    print(f"creatives: {sum(1 for v in verdicts if v['passed'])}/{len(verdicts)} pass")
    print("  wrote docs/results/C1-compliance.json")
    return 0 if payload["meets_target"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
