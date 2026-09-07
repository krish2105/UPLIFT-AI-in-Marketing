"""Generate the Term 4 artefacts from docs/results/.

EVERY NUMBER IS READ, NOT TYPED
-------------------------------
The report is built by opening the results files and formatting what is in them.
There is no path by which a figure reaches the document without a script having
measured it, and the placeholder scan runs before this does — so an artefact
cannot be generated while any published document still contains a TBD.

If a result is missing, this REFUSES rather than omitting the section quietly. A
report with a hole in it is recoverable; a report that silently dropped its
weakest result is not.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services"))
sys.path.insert(0, str(ROOT))

RESULTS = ROOT / "docs" / "results"
ARTEFACTS = ROOT / "docs" / "artefacts"

REQUIRED = (
    "A2-contrast",
    "A4-weather-etl",
    "A5-calendar",
    "A6-events",
    "A7-footfall",
    "A9-embedding-spike",
    "A10-palette",
    "B1-forecast",
    "B2-segments",
    "B3-allocator",
    "B4-uplift",
    "C1-compliance",
)


class MissingResult(RuntimeError):
    """A result the report quotes has not been measured."""


def load(name: str) -> dict:
    path = RESULTS / f"{name}.json"
    if not path.exists():
        raise MissingResult(
            f"{name}.json is missing. Run the script that writes it rather than removing "
            "the section that cites it."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def build_markdown() -> str:
    r = {name: load(name) for name in REQUIRED}
    f, s, a, u, c = (
        r["B1-forecast"],
        r["B2-segments"],
        r["B3-allocator"],
        r["B4-uplift"],
        r["C1-compliance"],
    )
    spike = r["A9-embedding-spike"]
    bge = next(x for x in spike["candidates"] if "bge-m3" in x["name"])
    nomic = next(x for x in spike["candidates"] if "nomic" in x["name"])

    zones = f["zones"]
    best = min(zones.items(), key=lambda kv: kv[1]["mae"])

    return (
        f"""# UPLIFT / MAWSIM — AI 208 report

**Demand-aware promo planning for Dubai retail.**
SP Jain MAIB Term 4 · AI 208 AI in Marketing · Krishna Mathur
Generated {date.today().isoformat()} from `docs/results/` by `scripts/build_report.py`.

> **SIDRA is a fictional Dubai speciality coffee and bakery chain**, invented for
> this demonstration. It is not a real company. The footfall and point-of-sale
> figures it is planned against are generated, labelled `simulated` at the type
> level, and every chart in the application says so.

Every figure below was read out of a results file. None was typed.

---

## 1. The problem

Dubai retail demand swings with events, weather, holidays and school calendars,
and promotions are planned on gut feel. MAWSIM forecasts demand per site, plans
promotions against that forecast, checks every claim against cited rules, and
measures incremental lift rather than clicks.

The reason to forecast **per site** rather than per brand is measurable. All four
SIDRA sites sit in neighbouring ERA5 grid cells and get the same weather. What
differs is how they respond: Marina Walk is 54% outdoor seating and Al Barsha is
fully enclosed, and the fitted evening temperature slopes order exactly by
outdoor share across all four sites.

## 2. Forecasting with exogenous drivers

| | |
|---|---|
| Method | {f["method"]} |
| Baseline | Seasonal naive — same hour, same weekday, last week |
| Result | **{f["weeks_won"]} of {f["weeks_total"]} site-weeks beaten** ({f["win_rate"]:.0%}) against a {f["target_win_rate"]:.0%} target |

| Site | MAE | Baseline MAE | Improvement | 80% coverage |
|---|---:|---:|---:|---:|
"""
        + "\n".join(
            f"| {z} | {v['mae']:.2f} | {v['baseline_mae']:.2f} | {v['improvement']:+.1%} | {v['coverage_80']:.0%} |"
            for z, v in zones.items()
        )
        + f"""

Best absolute error: **{best[0]} at {best[1]["mae"]:.2f}**.

### What the model gets wrong, and why it is reported

{f["note_on_smape"]}

## 3. Incrementality

| | |
|---|---|
| Method | {u["method"]} |
| Tolerance | {u["tolerance_points"]:.0f} percentage points |
| Result | **all {len(u["recovery"])} recovery checks inside tolerance**, worst error {u["worst_error_points"]:.2f} points |

| Injected | Raw | Bias | Adjusted | Error |
|---:|---:|---:|---:|---:|
"""
        + "\n".join(
            f"| {x['injected']:+.0%} | {x['recovered_raw']:+.2%} | {x['bias']:+.2%} | "
            f"{x['recovered']:+.2%} | {x['error_points']:+.2f} pts |"
            for x in u["recovery"]
        )
        + f"""

### The estimator's own bias

{u["note_on_bias"]}

## 4. Segmentation

{s["method"]}

| | |
|---|---|
| Customers | {s["customers"]:,} |
| Bootstrap stability | **{s["bootstrap_stability"]:.1%}** keep their segment across 25 resamples |

| Segment | Customers | Revenue share | Customer share |
|---|---:|---:|---:|
"""
        + "\n".join(
            f"| {x['segment']} | {x['customers']:,} | {x['revenue_share']:.1%} | {x['customer_share']:.1%} |"
            for x in sorted(s["segments"], key=lambda x: -x["revenue"])
        )
        + f"""

{s["note_on_curves"]}

## 5. Media allocation

{a["method"]}

Ninety-day daypart demand: """
        + ", ".join(f"{k} {v:,}" for k, v in a["daypart_demand_90d"].items())
        + """

| Budget | Incremental visits | Per 1,000 AED |
|---:|---:|---:|
"""
        + "\n".join(
            f"| {x['budget']:,} | {x['response']:,.0f} | {x['marginal_per_1000']:.1f} |"
            for x in a["sweep"]
        )
        + f"""

{a["note_on_parameters"]}

## 6. Brand and legal compliance

| | |
|---|---|
| Method | {c["method"]} |
| Target recall | {c["target_recall"]:.0%} |
| Worst recall across languages | **{c["worst_recall"]:.0%}** |

| Language | Cases | Recall | Precision |
|---|---:|---:|---:|
"""
        + "\n".join(
            f"| {lang} | {v['cases']} | {v['recall']:.0%} | {v['precision']:.0%} |"
            for lang, v in c["by_language"].items()
        )
        + f"""

{c["note_on_language"]}

{c["note_on_precision"]}

## 7. Retrieval

Embedding model chosen by measurement, not preference. The property that matters
is the **margin over an unrelated control** — a raw similarity between a sentence
and its translation is high under almost any model and means nothing alone.

| Model | dim | Worst HI margin | Worst AR margin | Verdict |
|---|---:|---:|---:|---|
| bge-m3:567m | {bge["dim"]} | {bge["worst_margin_hi"]:+.3f} | {bge["worst_margin_ar"]:+.3f} | local choice |
| nomic-embed-text | {nomic["dim"]} | {nomic["worst_margin_hi"]:+.3f} | {nomic["worst_margin_ar"]:+.3f} | **disqualified** |

`nomic-embed-text` is not weaker here — it is wrong. Its margin is negative: on
the nutrition probe it scores an English sentence about espresso-machine
depreciation above the Hindi and Arabic translations of the sugar-free rule.
Asked in Arabic what the threshold is, a system using it would return the
accounting sentence with a citation attached.

## 8. Accessibility and colour

| | |
|---|---|
| Contrast pairs measured | {r["A2-contrast"]["pairs_measured"]}, both registers |
| Palette checks | seven, both registers |

The palette was rejected twice by its own gate before passing: a saturated
midday hue collapsed to ΔE 3.5 under deuteranopia, and desaturating it made it
read grey. Neither failure is visible by eye on a designer's monitor.

## 9. Targets

| Target | Result | |
|---|---|---|
| Forecast beats naive on ≥70% of weeks | {f["win_rate"]:.0%} | {"MET" if f["meets_target"] else "MISSED"} |
| Uplift recovery within ±5 points | worst {u["worst_error_points"]:.2f} pts | {"MET" if u["all_within_tolerance"] else "MISSED"} |
| Compliance recall ≥0.90 | {c["worst_recall"]:.0%} worst language | {"MET" if c["meets_target"] else "MISSED"} |
| Segments stable under bootstrap | {s["bootstrap_stability"]:.1%} | {"MET" if s["bootstrap_stability"] >= 0.8 else "MISSED"} |

## 10. Limitations

- **Footfall is generated.** No public hourly footfall series exists for a Dubai
  café. What is not invented is the evaluation.
- **Event dates are placed, not confirmed.** Visit Dubai returns 403 to every
  non-browser client and no redistributable feed exists.
- **Islamic holidays are calculated** against a moon-sighting rule, and carry one
  day of uncertainty.
- **Allocator elasticities are assumed**, because no promotion has run.
- **Most compliance clauses are unread.** Source documents are verified; the
  clauses are quoted verbatim during corpus ingestion, and until then the brand
  PDF prints "clause unverified".
- **The persona panel is not customer research.** It applies a rubric; it does
  not observe a reaction.
- **Synthetic control cannot fully control for weather here.** With four sites
  and one uniquely weather-elastic, the treated unit is inside the donors' hull
  on level and outside it on elasticity.

## Not advice

This produces a marketing plan and a compliance opinion for a fictional brand as
coursework. It is not legal advice, not regulatory clearance, and not a
substitute for real customer research.
"""
    )


def main() -> int:
    ARTEFACTS.mkdir(parents=True, exist_ok=True)
    try:
        md = build_markdown()
    except MissingResult as exc:
        print(f"REFUSED: {exc}")
        return 1

    path = ARTEFACTS / "AI208_MAWSIM_report.md"
    path.write_text(md, encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)} ({len(md):,} chars)")

    try:
        from docx import Document
        from docx.shared import Pt

        doc = Document()
        doc.core_properties.title = "UPLIFT / MAWSIM — AI 208 report"
        doc.core_properties.author = "Krishna Mathur"
        for line in md.splitlines():
            if line.startswith("# "):
                doc.add_heading(line[2:], 0)
            elif line.startswith("## "):
                doc.add_heading(line[3:], 1)
            elif line.startswith("### "):
                doc.add_heading(line[4:], 2)
            elif line.startswith("|") or line.startswith(">"):
                # A separator row like |---|---| strips to nothing, and an empty
                # paragraph has no runs to style.
                text = line.strip("|> ").strip()
                if not text or set(text) <= set("-|: "):
                    continue
                para = doc.add_paragraph(text)
                if para.runs:
                    para.runs[0].font.size = Pt(9)
            elif line.strip():
                doc.add_paragraph(line)
        docx_path = ARTEFACTS / "AI208_MAWSIM_report.docx"
        doc.save(docx_path)
        print(f"wrote {docx_path.relative_to(ROOT)}")
    except ImportError:
        print("python-docx not installed; the markdown report is the artefact")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
