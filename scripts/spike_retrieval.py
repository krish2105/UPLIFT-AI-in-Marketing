"""Can the vector half answer on its own? Measure it, then decide.

The vector half was added for one capability BM25 cannot have: an Arabic or
Hindi question reaching an English passage. Cosine ranks EVERY passage, though,
so a retriever that trusts it will always return something — and this project's
Ask contract is that it refuses rather than guesses.

So the question is not "is the embedder good" (A9 answered that) but "does
similarity separate a real question from one this corpus cannot answer". That is
a threshold question, and a threshold nobody measured is a threshold set to
whatever made the demo work.

The probe set is deliberately unkind: the in-domain side includes ONE-WORD
queries, which have the least to embed, and the out-of-domain side includes
fluent, plausible-sounding questions rather than keyboard mash — because
"pineapple submarine tuesday" is not what a confused user types.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

from pipeline.common import now_iso  # noqa: E402
from services.api.rag import corpus, vectors  # noqa: E402

RESULTS = ROOT / "docs" / "results"

IN_DOMAIN = [
    ("en", "sugar-free claim rule"),
    ("en", "detox"),
    ("en", "does weather affect demand"),
    ("en", "which site has the most outdoor seating"),
    ("ar", "ما هي قاعدة السكر"),
    ("ar", "هل يؤثر الطقس على الطلب"),
    ("hi", "क्या मौसम मांग को प्रभावित करता है"),
    ("hi", "शुगर फ्री दावे का नियम"),
]

OUT_OF_DOMAIN = [
    ("en", "who wrote this report"),
    ("en", "what is the capital of Peru"),
    ("en", "how do I reset my password"),
    ("en", "what were quarterly earnings per share"),
    ("ar", "ما هو عدد سكان القاهرة"),
    ("hi", "भारत की राजधानी क्या है"),
    # Added after the first bar leaked. Both are office-shaped requests aimed at
    # a marketing tool — the plausible wrong question, not the absurd one — and
    # "send me the invoice" scored high enough to be admitted by a bar
    # calibrated without it. The threshold is derived from this list, so growing
    # the list is how the bar gets corrected; hand-raising it would have been
    # fitting the number to the one example that embarrassed it.
    ("en", "when is the next board meeting"),
    ("en", "send me the invoice"),
    ("en", "book a table for four at seven"),
    ("en", "what is our refund policy"),
]


def main() -> int:
    e = vectors.embedder()
    if e is None:
        print("no embedder available; this spike needs one and refuses to guess without it")
        return 1

    passages, _ = corpus.build()
    matrix = e.embed([p.text for p in passages])

    def probe(q: str) -> dict:
        sims = vectors.cosine(e.embed([q])[0], matrix)
        order = np.argsort(-sims)
        return {
            "query": q,
            "max": round(float(sims.max()), 4),
            "median": round(float(np.median(sims)), 4),
            "gap": round(float(sims.max() - np.median(sims)), 4),
            "top": passages[int(order[0])].id,
        }

    inside = [{"lang": lang, **probe(q)} for lang, q in IN_DOMAIN]
    outside = [{"lang": lang, **probe(q)} for lang, q in OUT_OF_DOMAIN]

    worst_in = min(x["max"] for x in inside)
    best_out = max(x["max"] for x in outside)
    separable = worst_in > best_out

    # If any threshold exists, it is the midpoint; if none does, say so rather
    # than quietly picking one that fits the examples used to find it.
    threshold = round((worst_in + best_out) / 2, 3) if separable else None

    # The fallback question: is there a HIGH bar that no out-of-domain query
    # reaches, even if some in-domain queries also miss it? That is a weaker but
    # still useful claim — it licenses the vector half to answer alone only for
    # queries above it.
    high_bar = round(best_out + 0.02, 3)
    reachable = [x["query"] for x in inside if x["max"] >= high_bar]

    # The similarity table is diagnostic. What the application actually does is
    # run search(), so that is measured too — a threshold study that never calls
    # the function it is tuning is a study of a number, not of a retriever.
    answered, refused, lost = [], [], []
    for lang, q in IN_DOMAIN:
        hits = corpus.search(q, 3)
        (answered if hits else lost).append(
            {
                "lang": lang,
                "query": q,
                "top": hits[0]["id"] if hits else None,
                "matched_by": hits[0]["matched_by"] if hits else None,
            }
        )
    leaked = []
    for lang, q in OUT_OF_DOMAIN:
        hits = corpus.search(q, 3)
        (leaked if hits else refused).append(
            {"lang": lang, "query": q, "top": hits[0]["id"] if hits else None}
        )

    payload = {
        "task": "C2-retrieval",
        "generated_by": "scripts/spike_retrieval.py",
        "generated_at": now_iso(),
        "embedder": {"backend": e.kind, "model": e.model},
        "corpus_passages": len(passages),
        "in_domain": inside,
        "out_of_domain": outside,
        "worst_in_domain_max": worst_in,
        "best_out_of_domain_max": best_out,
        "separable_by_a_single_threshold": separable,
        "threshold": threshold,
        "high_bar": high_bar,
        "queries_clearing_the_high_bar": reachable,
        "decision": (
            "A single similarity threshold separates in-domain from out-of-domain, "
            f"and it is {threshold}. The vector half may answer alone above it."
            if separable
            else "NO single similarity threshold separates them, and the overlap is "
            "not marginal: the best out-of-domain probe outscores every in-domain "
            "question but one. A short query has almost nothing to embed, and an "
            "office-shaped request like 'send me the invoice' reads as close to a "
            f"brand-voice rule about being concrete. The bar lands at {high_bar}, "
            "above all but one real question, so in practice the vector half no "
            "longer ADMITS anything: it re-ranks what the lexical half has already "
            "vouched for. That is a smaller retriever than the one the A9 spike "
            "seemed to promise, and it is the one the refusal contract permits. A "
            "cross-lingual answer that arrives alongside an invoice request is not "
            "a feature."
        ),
        "end_to_end": {
            "in_domain_answered": len(answered),
            "in_domain_total": len(IN_DOMAIN),
            "out_of_domain_refused": len(refused),
            "out_of_domain_total": len(OUT_OF_DOMAIN),
            "answered": answered,
            "unanswered_in_domain": lost,
            "leaked_out_of_domain": leaked,
        },
        "what_the_losses_are": (
            "The in-domain questions that go unanswered are the non-English ones about "
            "WEATHER and DEMAND, and the reason is structural rather than a tuning "
            "miss: the zone and dataset passages are English prose, while the only "
            "Arabic and Devanagari tokens in the corpus are the regex triggers inside "
            "the claim rules. So a non-English question about a RULE lands, and a "
            "non-English question about the DATA has nothing in its own script to land "
            "on. Vectors could bridge exactly that gap, and the measurement above is "
            "why they are not allowed to: the bar that admits those two also admits "
            "'send me the invoice'. Translating the zone and dataset passages is the "
            "fix, and it is a content job rather than a retrieval one."
        ),
        "why_this_is_not_a_failure": (
            "Cosine over 39 passages was never going to be a domain classifier. The "
            "spike's job was to find out before the design depended on it, and the "
            "design now depends on the lexical half for admission and the vector half "
            "for reach — which is what a hybrid retriever is supposed to be."
        ),
    }

    RESULTS.mkdir(parents=True, exist_ok=True)
    out = RESULTS / "C2-retrieval.json"
    if out.exists():
        prev = json.loads(out.read_text(encoding="utf-8"))
        if {k: v for k, v in prev.items() if k != "generated_at"} == {
            k: v for k, v in payload.items() if k != "generated_at"
        }:
            payload["generated_at"] = prev["generated_at"]
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"in-domain worst max   {worst_in:.4f}")
    print(f"out-of-domain best max {best_out:.4f}")
    print(
        f"separable: {separable}  high bar: {high_bar}  clears it: {len(reachable)}/{len(inside)}"
    )
    print("  wrote docs/results/C2-retrieval.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
