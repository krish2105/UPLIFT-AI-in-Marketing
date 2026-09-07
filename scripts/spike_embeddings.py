"""Choose the embedding model by measurement, and record the measurement.

WHAT IS ACTUALLY BEING TESTED
-----------------------------
UPLIFT answers questions in English, Hindi and Arabic against one corpus: the
SIDRA brand guidelines, Codex nutrition-claim guidance, UAE consumer-protection
guidance and event listings. An Arabic question must retrieve the English clause
that answers it. So the property that matters is CROSS-LINGUAL ALIGNMENT, and
the way to see it is not the raw similarity between a sentence and its
translation — that number is high for almost any model and means nothing on its
own.

What means something is the MARGIN over an unrelated control: how much closer
the model puts a translation than it puts a sentence about something else. A
model whose margin is small will, on a real query, rank an unrelated chunk above
the correct one and hand back an answer with a citation attached. A confidently
wrong answer with provenance is worse than no answer.

THE CONTROLS ARE DELIBERATELY HARD
----------------------------------
They are drawn from the same business and the same document set as the probes —
depreciation policy, a compliance verdict — rather than from an unrelated topic.
An easy control (a sentence about astronomy) inflates every margin and would
make a bad model look usable.

Bar: margin >= 0.25 on BOTH the Hindi and the Arabic pair, on every probe.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "docs" / "results" / "A9-embedding-spike.json"
MARGIN_BAR = 0.25

#: Three probes from the corpus this project actually retrieves over.
PROBES: list[dict[str, str]] = [
    {
        "id": "weather-elasticity",
        "en": "Marina Walk's outdoor seating empties when the evening apparent temperature passes 38 degrees.",
        "hi": "मरीना वॉक की बाहरी बैठक खाली हो जाती है जब शाम को महसूस होने वाला तापमान 38 डिग्री से ऊपर चला जाता है।",
        "ar": "تفرغ المقاعد الخارجية في مرسى دبي عندما تتجاوز درجة الحرارة المحسوسة مساءً 38 درجة.",
    },
    {
        "id": "nutrition-claim",
        "en": "A sugar-free claim requires the drink to contain no more than half a gram of sugars per hundred millilitres.",
        "hi": "शुगर-फ्री का दावा करने के लिए पेय में प्रति सौ मिलीलीटर आधा ग्राम से अधिक शर्करा नहीं होनी चाहिए।",
        "ar": "يشترط ادعاء «خالٍ من السكر» ألا يحتوي المشروب على أكثر من نصف غرام من السكريات لكل مائة مليلتر.",
    },
    {
        "id": "ramadan-shape",
        "en": "During Ramadan the daytime trade collapses and the hours after iftar carry the whole day.",
        "hi": "रमज़ान के दौरान दिन का कारोबार गिर जाता है और इफ़्तार के बाद के घंटे पूरे दिन का भार उठाते हैं।",
        "ar": "خلال رمضان تنهار حركة البيع نهاراً وتتحمل الساعات التي تلي الإفطار عبء اليوم كله.",
    },
]

#: Same business, same document set, different meaning. See the header.
CONTROLS: list[str] = [
    "Depreciation on the espresso machines is charged on a straight-line basis over five years.",
    "The compliance agent recorded two citations against the brand guidelines section on superlatives.",
    "Delivery aggregator commission is settled on the fifteenth of the following month.",
]


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))


# ── backends ────────────────────────────────────────────────────────────────


def embed_ollama(model: str, texts: list[str]) -> tuple[np.ndarray, float]:
    host = (os.getenv("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    t0 = time.perf_counter()
    r = httpx.post(f"{host}/api/embed", json={"model": model, "input": texts}, timeout=180.0)
    r.raise_for_status()
    return np.array(r.json()["embeddings"], dtype=float), time.perf_counter() - t0


def embed_fastembed(model: str, texts: list[str]) -> tuple[np.ndarray, float]:
    from fastembed import TextEmbedding

    t0 = time.perf_counter()
    emb = TextEmbedding(model_name=model)
    vectors = np.array(list(emb.embed(texts)), dtype=float)
    return vectors, time.perf_counter() - t0


CANDIDATES: list[dict] = [
    {
        "name": "bge-m3:567m",
        "backend": "ollama",
        "deployable": False,
        "note": "Local. 8192-token context, which is what matters for reading a page of a PDF.",
    },
    {
        "name": "nomic-embed-text",
        "backend": "ollama",
        "deployable": False,
        "note": "Local. English-first; included to test whether it is usable here at all.",
    },
    {
        "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "backend": "fastembed",
        "deployable": True,
        "note": "ONNX, 0.22 GB. The only candidate small enough to consider on a free dyno.",
    },
    {
        "name": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "backend": "fastembed",
        "deployable": True,
        "note": "ONNX, 1.0 GB. Will not fit a 512 MB instance; measured for comparison.",
    },
]


def evaluate(candidate: dict) -> dict:
    texts: list[str] = []
    for p in PROBES:
        texts += [p["en"], p["hi"], p["ar"]]
    texts += CONTROLS

    embed = embed_ollama if candidate["backend"] == "ollama" else embed_fastembed
    try:
        vecs, seconds = embed(candidate["name"], texts)
    except Exception as exc:  # noqa: BLE001 — a missing model is a result, not a crash
        return {**candidate, "available": False, "error": f"{type(exc).__name__}: {exc}"[:200]}

    per_probe = []
    for i, p in enumerate(PROBES):
        en, hi, ar = vecs[i * 3], vecs[i * 3 + 1], vecs[i * 3 + 2]
        ctrl = vecs[len(PROBES) * 3 :]
        # The hardest control is the one that matters: a model is only safe if
        # its worst case clears the bar.
        control_max = max(cosine(en, c) for c in ctrl)
        s_hi, s_ar = cosine(en, hi), cosine(en, ar)
        per_probe.append(
            {
                "probe": p["id"],
                "en_hi": round(s_hi, 4),
                "en_ar": round(s_ar, 4),
                "hardest_control": round(control_max, 4),
                "margin_hi": round(s_hi - control_max, 4),
                "margin_ar": round(s_ar - control_max, 4),
            }
        )

    worst_hi = min(r["margin_hi"] for r in per_probe)
    worst_ar = min(r["margin_ar"] for r in per_probe)
    return {
        **candidate,
        "available": True,
        "dim": int(vecs.shape[1]),
        "seconds_for_12_texts": round(seconds, 2),
        "probes": per_probe,
        "worst_margin_hi": worst_hi,
        "worst_margin_ar": worst_ar,
        "clears_bar": bool(worst_hi >= MARGIN_BAR and worst_ar >= MARGIN_BAR),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--skip-fastembed",
        action="store_true",
        help="skip the ONNX candidates (they download ~1.2 GB on first run)",
    )
    args = ap.parse_args()

    results = []
    for c in CANDIDATES:
        if args.skip_fastembed and c["backend"] == "fastembed":
            results.append({**c, "available": False, "error": "skipped by flag"})
            continue
        print(f"  measuring {c['name']} ...", flush=True)
        results.append(evaluate(c))

    usable = [r for r in results if r.get("clears_bar")]
    local = [r for r in usable if r["backend"] == "ollama"]
    deployable = [r for r in usable if r.get("deployable")]

    payload = {
        "task": "A9-embedding-spike",
        "generated_by": "scripts/spike_embeddings.py",
        "margin_bar": MARGIN_BAR,
        "method": (
            "Cosine similarity between an English sentence and its Hindi and Arabic "
            "translations, minus the similarity to the closest of three unrelated "
            "controls drawn from the same business. The margin is what matters; a "
            "raw similarity is high for almost any model and means nothing alone."
        ),
        "probes": [p["id"] for p in PROBES],
        "controls": CONTROLS,
        "candidates": results,
        "decision": {
            "local": local[0]["name"] if local else None,
            "deployed": deployable[0]["name"] if deployable else None,
            "disqualified": [
                r["name"] for r in results if r.get("available") and not r.get("clears_bar")
            ],
        },
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print()
    for r in results:
        if not r.get("available"):
            print(f"  {r['name'][:52]:52} unavailable — {r.get('error', '')[:40]}")
            continue
        mark = "USABLE    " if r["clears_bar"] else "DISQUALIFIED"
        print(
            f"  {r['name'][:52]:52} dim={r['dim']:>5}  "
            f"margin hi/ar {r['worst_margin_hi']:+.3f}/{r['worst_margin_ar']:+.3f}  {mark}"
        )
    print(f"\nlocal: {payload['decision']['local']}\ndeployed: {payload['decision']['deployed']}")
    print(f"wrote {RESULTS.relative_to(ROOT)}")

    if not local:
        print("\nFAIL: no local model clears the bar.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
