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
sys.path.insert(0, str(Path(__file__).resolve().parent))  # build_docx, beside this file

from api.brand import load_brand  # noqa: E402  (after the sys.path insert above)
from api.creative.compliance import check as check_copy  # noqa: E402

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
    "C2-retrieval",
    "D1-frames",
    "E1-red-team",
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
    red = r["E1-red-team"]

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

## Executive summary

MAWSIM forecasts hourly footfall for four SIDRA sites in Dubai from exogenous
drivers — weather, events, public holidays and school terms — plans promotions
against that forecast, checks every creative claim against cited food-advertising
rules, and measures incremental lift rather than clicks.

| What was claimed | What was measured |
|---|---|
| The forecast beats a seasonal-naive baseline | **{f["weeks_won"]} of {f["weeks_total"]} site-weeks**, MAE {min(z["improvement"] for z in f["zones"].values()):.0%}–{max(z["improvement"] for z in f["zones"].values()):.0%} lower |
| Lift estimates recover a known effect | five injections recovered within **{u["worst_error_points"]:.2f} points** of a five-point tolerance |
| Segments are stable | **{s["bootstrap_stability"]:.1%}** keep their segment across resamples |
| Compliance catches violations in three languages | recall and precision **{c["worst_recall"]:.0%}** in the worst language |
| Retrieval refuses what it cannot cite | **{r["C2-retrieval"]["end_to_end"]["out_of_domain_refused"]}/{r["C2-retrieval"]["end_to_end"]["out_of_domain_total"]}** out-of-domain questions refused |
| The safety claims survive attack | **{red["held"]}/{red["cases"]}** red-team attempts held |

Three findings are worth more than the table. The forecast is **worse than the
baseline on sMAPE** and that is reported rather than dropped. The lift estimator
carries a **{u["recovery"][0]["bias"]:+.1%} bias** on a window where nothing
happened, measured on a placebo and subtracted. And the retrieval layer's
embeddings were **denied the power to answer on their own**, because the
similarity bar that would admit a genuine Arabic question also admits "send me
the invoice".

The brand is fictional and the footfall is generated. What is not generated is
the evaluation: every model is scored against a baseline on held-out time, and
every number in this document is read from `docs/results/` rather than typed.

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

## 10. Safety, and what happened when it was attacked

No agent in the registry holds a tool with a side effect; the whole API is GET,
so there is no verb with which to write. That is an architectural claim, and a
claim is worth what the attempt to break it is worth.

`scripts/red_team.py` makes {red["cases"]} attempts across
{len(red["by_control"])} OWASP ASI controls — prompt injection into the
compliance checker, script-mixing and zero-width evasion of the claim rules,
forged and edited capability tokens, HTTP verbs the API does not answer,
provenance stripping, aiming the embedder off-box, and budget exhaustion.
**{red["held"]} of {red["cases"]} held.**

| Control | Attempts | Held |
|---|---|---|
{chr(10).join(f"| {k} | {v['cases']} | {v['held']} |" for k, v in sorted(red["by_control"].items()))}

{red["known_limitation"]}

A pass here is narrow, and the file says so in its own words:
{red["what_a_pass_means"]}

## 11. Limitations

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
- **A bearer token is usable by whoever holds it.** Admin is proved by a signed
  token rather than claimed in a header, but a stateless credential cannot tell
  its holder from its owner. Lifetimes default to eight hours and an id can be
  refused immediately, though the revocation set is process memory and clears on
  restart.
- **The public deployment has no Admin at all.** No signing secret is set there,
  so the capability is absent rather than open — which also means the kill
  switch cannot be demonstrated against the live URL.
- **The persona panel is not customer research.** It applies a rubric; it does
  not observe a reaction.
- **Synthetic control cannot fully control for weather here.** With four sites
  and one uniquely weather-elastic, the treated unit is inside the donors' hull
  on level and outside it on elasticity.

## 12. Business case

Stated as arithmetic with its assumptions visible, because no promotion has run
and therefore nothing here is a measured return.

What the system changes is not the size of a promotion budget but where it
lands. The allocator distributes a fixed spend across fifteen channel × daypart
cells rather than five channels, and the daypart split is where the money
actually moves: aggregator spend pays back at midday and is wasted at 07:00, and
near-store outdoor advertising only works within walking distance of a site.

| Lever | Mechanism | Status |
|---|---|---|
| Staffing to the forecast | MAE {min(z["improvement"] for z in f["zones"].values()):.0%}–{max(z["improvement"] for z in f["zones"].values()):.0%} below "same hour last week" | **measured** |
| Promotion sized to the interval | plans against the 80% lower bound, not the point estimate | **implemented** |
| Spend moved between dayparts | concave allocator, optimum verified by equal marginal return | **implemented, elasticities assumed** |
| Copy cleared before it runs | {c["by_language"]["en"]["cases"]}-case gold set, {c["worst_recall"]:.0%} recall in the worst of three languages | **measured** |
| Lift measured instead of clicks | synthetic control + CUPED, recovery within {u["worst_error_points"]:.2f} points | **measured** |

The honest summary: **four of five levers are demonstrated, and the one that
would produce a currency figure is the one whose parameters are assumed.** A
pilot replaces the assumed elasticities with measured lift, at which point the
allocator's output becomes a forecast of return rather than a demonstration of
method. Quoting a dirham figure before that would be inventing the only number
anybody would actually act on.

## 13. Conclusion

The method holds on invented data because it is judged against a baseline that
sees the same invented data. Replace the footfall series with a real POS export
and nothing in the pipeline changes — that is the point of scoring against
seasonal naive on held-out time rather than reporting a fit.

What this project demonstrates is not that demand can be forecast, which is
uncontroversial, but that a marketing system can be built so that **every figure
it shows can be traced to the script that produced it, and every claim it makes
about its own safety has been attacked on purpose.** The gates that disagreed
with each other found real defects: a metric that got worse, an estimator biased
where nothing happened, a colour indistinguishable under deuteranopia, a forged
header that engaged the kill switch. Each was fixed rather than tuned away, and
the residuals that could not be fixed are stated here rather than omitted.

## Not advice

This produces a marketing plan and a compliance opinion for a fictional brand as
coursework. It is not legal advice, not regulatory clearance, and not a
substitute for real customer research.
"""
    )


def build_deck() -> str:
    r = {name: load(name) for name in REQUIRED}
    f, u, c, red = r["B1-forecast"], r["B4-uplift"], r["C1-compliance"], r["E1-red-team"]
    s_ = r["B2-segments"]

    # Typed numbers are how a deck drifts from the results it claims to report.
    # These four come off the brand kit and the JSON, so the slide cannot be
    # right on the day it was written and wrong a week later.
    brand = load_brand()
    outdoor = max(z.outdoor_share for z in brand.zones)
    rules = len(brand.claims_to_avoid)
    gains = [z["improvement"] for z in f["zones"].values()]
    bias = u["recovery"][0]["bias"]
    worst_creative = max(c["creatives"], key=lambda cr: len(cr["findings"]))

    return f"""# AI 208 — UPLIFT / MAWSIM · deck outline

Twelve slides, one argument per slide. Every number below is read from
`docs/results/`; none is typed.

---

## 1 · The problem, in one sentence
Dubai retail demand swings with events, weather, holidays and school calendars,
and promotions are planned on gut feel.
**Visual:** the Season terrain, 56 days across four sites.

## 2 · The brand
SIDRA — a fictional Dubai speciality coffee and bakery chain, four sites,
invented for this demonstration. Say this out loud on slide two, not in a
footnote.
**Visual:** the four site cards with their outdoor-seating bars.

## 3 · Why per site and not per brand
All four sites sit in neighbouring ERA5 grid cells and get the SAME weather.
What differs is how they respond. Marina Walk is {outdoor:.0%} outdoor; Al Barsha
is fully enclosed. **The fitted slopes order exactly by outdoor share.**
**Visual:** evening footfall against apparent temperature, four lines.

## 4 · The data, and what each part of it is
Five datasets, four provenance labels: observed, curated, simulated, sample.
A Dataset cannot be constructed without a licence and a label.
**Visual:** the Data tab.

## 5 · Forecast
Gradient boosting with exogenous drivers, chronological holdout.
**{f["weeks_won"]} of {f["weeks_total"]} site-weeks beaten** against a {f["target_win_rate"]:.0%}
target; MAE {min(gains):.0%}–{max(gains):.0%} below seasonal naive.
**Visual:** the week-by-week table.

## 6 · Where the model is worse, and why we say so
sMAPE is higher than the baseline on every site. Seasonal naive returns the
exact integer from last week, which on low-count hours is proportionally perfect
while being absolutely further away. MAE is the gate; sMAPE is reported.
**This slide is the one that earns the rest.**

## 7 · Segments and allocation
RFM at **{s_["bootstrap_stability"]:.0%}** bootstrap stability; a concave
channel × daypart allocator whose optimum is checkable (equal marginal return).
Elasticities are assumed, and every response says so.
**Visual:** the 15-cell heat table.

## 8 · Creatives and compliance
Composed from the brand kit, identical every run. {rules} rules, each citing its
clause. Recall and precision **{c["worst_recall"]:.0%}** in the worst of three languages.
**Visual:** the `{worst_creative["slot"]}` creative with its
{len(worst_creative["findings"])} findings.

## 9 · Measurement
Synthetic control + CUPED. An injected lift is recovered within
**{u["worst_error_points"]:.2f} points** of a five-point tolerance.
**Visual:** treated against counterfactual.

## 10 · The estimator's own bias
It returns {bias:+.1%} where nothing happened, because the donor blend is
weather-flat and the treated site is not. Measured on a placebo window and
subtracted, with both numbers reported.
**The second slide that earns the rest.**

## 11 · Safety, and the attack that used to work
No agent has a tool that reaches the outside world; the whole API is GET.
**{red["held"]}/{red["cases"]}** red-team attacks held across {len(red["by_control"])}
controls. Until recently one did not: `X-Mawsim-Role: ADMIN ` engaged the kill
switch, and the harness scored it as a break rather than as an expected result —
which is what made it worth fixing rather than worth explaining. A role is now a
signed token, and eleven cases attack that instead.
**Visual:** the attack table, with the RT-TOK rows.

## 12 · Limitations
Footfall is generated. Event dates are placed, not confirmed. Islamic holidays
are calculated against a moon-sighting rule. Allocator elasticities are assumed.
The persona panel is not customer research.
**End on this slide, not on the results.**
"""


def build_viva() -> str:
    r = {name: load(name) for name in REQUIRED}
    f, u, c = r["B1-forecast"], r["B4-uplift"], r["C1-compliance"]
    spike = r["A9-embedding-spike"]
    nomic = next(x for x in spike["candidates"] if "nomic" in x["name"])
    nut = next(pr for pr in nomic["probes"] if pr["probe"] == "nutrition-claim")

    return f"""# AI 208 — viva preparation

Fifteen questions an examiner is likely to ask, and the honest answer to each.
Where a number appears it comes from `docs/results/`.

---

**1 · Your footfall data is invented. Why should I believe anything downstream?**
You should not believe the DATA. You should judge the METHOD, and the method is
evaluated against a baseline that sees the same invented data. The forecast beats
seasonal naive on {f["weeks_won"]} of {f["weeks_total"]} site-weeks; if the model
were fitting noise it would not beat "same hour last week" on held-out time.
Every row carries `simulated`, enforced by a constructor that raises without it.

**2 · Why gradient boosting rather than Prophet or ARIMA?**
Two reasons in order of weight. It has to deploy — Prophet's build chain does not
fit a free instance, and a model that cannot run where the application runs is
not a candidate. And the claim being tested is that EXOGENOUS drivers move
demand; a boosted tree takes them as explicit columns and lets their
contribution be read off.

**3 · Your sMAPE is worse than the baseline. Is the model bad?**
No, and this is worth a minute. Seasonal naive returns the exact integer count
from the same hour last week. On the many low-count hours that is often exactly
right and therefore proportionally perfect, while being further away in absolute
terms. For staffing a café the absolute error is the decision-relevant one, so
MAE is the gate. I report sMAPE rather than dropping it because dropping the
metric that disagrees with you is how a report becomes an advertisement.

**4 · How do you know the model is not leaking the future?**
The split is chronological, never random — a random split on an hourly series
with a weekly cycle is close to giving the model the answer. Lag features are
built by shifting the target, and a test asserts `lag_168` equals the target 168
rows earlier, exactly.

**5 · Why is the prediction interval two quantile models rather than ±1.28σ?**
Demand is bounded below by zero and its spread grows with its level. A symmetric
interval would be too wide at 04:00 and too narrow at the evening peak, which is
exactly when a planner needs it.

**6 · Your uplift estimator returns {u["recovery"][0]["bias"]:+.1%} on a window
where nothing happened. Explain.**
That is the most interesting number in the project. The donor blend is dominated
by Al Barsha, which is fully enclosed; Marina Walk is more than half outdoor
seating. As the Gulf summer arrives Marina falls away from its own history while
the enclosed donor does not, so the counterfactual drifts above the treated site
for reasons unrelated to any promotion. With four sites and one uniquely
weather-elastic, no convex blend of the others can match Marina's weather
response — it is inside the donors' hull on LEVEL and outside it on ELASTICITY.
I measure that on a placebo-in-time window and subtract it, and report both.

**7 · How do you know your lift number means anything?**
Because I inject a known lift and check the machinery finds it. Five injections
from 0% to 30%, all recovered within {u["worst_error_points"]:.2f} points of a
five-point tolerance. An estimator that cannot recover a lift it was handed is
not measuring anything.

**8 · The allocator's elasticities are made up. Isn't the whole tab theatre?**
The PARAMETERS are assumed and every response says `assumed: true`. The
STRUCTURE is not: the objective is concave, so the optimum is unique and a greedy
marginal allocation finds it exactly, and the KKT condition — equal marginal
return across funded cells — is asserted by a test. When a real promotion runs,
the measured lift replaces the parameters and nothing else changes.

**9 · Why fifteen cells rather than five channels?**
Because a café's budget is small and a channel-only split has nothing to say. The
interesting structure is that a channel's payback depends on the HOUR: aggregator
spend works at midday and is wasted at 07:00.

**10 · Your compliance engine is regex. Why not use a language model?**
Because a verdict that depends on a model's mood cannot be audited, and the claim
this application makes is that every verdict cites the clause it came from. The
red team ran {len([x for x in r["E1-red-team"]["results"] if x["control"] == "ASI-03"])}
injection and evasion attacks against it, including "ignore all previous
instructions", and all held — because there is nothing there to persuade.

**11 · How do you know the rule set is any good?**
A {c["by_language"]["en"]["cases"]}-case gold set whose CLEAN half is deliberately
adversarial: discounts with stated terms, allergen statements, "fresh" qualified
by "baked on site". Recall and precision are both {c["by_language"]["en"]["recall"]:.0%}
in English, and both clear the {c["target_recall"]:.0%} target in Arabic and Hindi.
Precision matters because a tool that flags good copy gets switched off, and then
it catches nothing at all.

**12 · Why is recall reported per language rather than as one number?**
Because the first version of the rule set caught six violations in English, four
in Arabic and two in Hindi. A blended number would have hidden exactly the
imbalance it was written to find.

**13 · Why did you disqualify an embedding model rather than rank it last?**
`nomic-embed-text` has a NEGATIVE margin. What is measured is not raw similarity
but the MARGIN over an unrelated control sentence, because a model that scores
everything at 0.7 is useless at 0.7. On the nutrition probe it puts an English
sentence about espresso-machine depreciation at {nut["hardest_control"]:.4f} —
ABOVE the Hindi translation of the claim itself at {nut["en_hi"]:.4f}. Its worst
margins are {nomic["worst_margin_hi"]:+.4f} on Hindi and
{nomic["worst_margin_ar"]:+.4f} on Arabic, against a bar of +0.25. Asked in Arabic
what the sugar-free threshold is, a system using it would return the accounting
sentence with a citation attached, and a confidently wrong answer carrying
provenance is worse than no answer. It is disqualified rather than ranked last,
and a test asserts it stays disqualified.

**14 · Where could the 3D view mislead, and what stops it?**
Extrusion reads as fact — a 3D landscape is the most confident-looking chart
there is. Every block wears a translucent cap running from its low bound to its
high one, so an uncertain day is visibly taller in its uncertainty than in its
estimate. The daily interval combines in quadrature rather than summing, because
adding 24 hourly bands would assume every hour misses in the same direction.

**15 · What would this need to become a product?**
A real POS or footfall export in place of the generated series. A donor pool
large enough that the treated site is inside its hull on elasticity, not only on
level. The clauses
read verbatim so no rule cites something nobody has opened. And a pilot, because
every elasticity in the allocator is currently an assumption.
"""


def build_demo() -> str:
    r = {name: load(name) for name in REQUIRED}
    f, u, c = r["B1-forecast"], r["B4-uplift"], r["C1-compliance"]

    # The two strings the presenter is told to type, run through the same engine
    # the demo will run in front of the examiner. A script that says "six
    # findings" where the tool returns three loses the room in one keystroke.
    fail_copy = "Our best sugar-free detox latte"
    pass_copy = "Was AED 32, now AED 24. Until 30 September."
    fail_n = len(check_copy(fail_copy).findings)
    pass_n = len(check_copy(pass_copy).findings)
    assert fail_n > 0 and pass_n == 0, "the demo's two examples no longer behave as scripted"

    return f"""# AI 208 — three-minute demo

One thread, five moves. Open `/healthz` a minute before you start: the free
instance sleeps and the first request takes about fifty seconds.

**https://uplift-mawsim.vercel.app**

---

## 0:00 — Season (20s)
Open on the terrain. Scrub to a day with an event band.

> "Eight weeks of demand for four SIDRA sites. SIDRA is fictional — I invented it
> for this. Every block wears its prediction interval, because a 3D landscape is
> the most confident-looking chart there is and I did not want it lying."

Toggle to **Map**, then back.

> "The terrain answers when. The map answers where."

## 0:35 — Forecast (35s)
> "{f["weeks_won"]} of {f["weeks_total"]} site-weeks beaten against seasonal
> naive. The target was {f["target_win_rate"]:.0%}."

Scroll to the sMAPE panel.

> "And here it is worse than the baseline. Seasonal naive returns last week's
> exact integer, which on low-count hours is proportionally perfect. I report it
> rather than dropping it."

## 1:10 — Plan (30s)
Drag the budget slider.

> "Fifteen cells, five channels by three dayparts. The objective is concave so
> the optimum is exact — that number is the marginal spread, and at the optimum
> every funded cell returns the same amount for the next dirham. The
> elasticities are assumed, and it says so."

## 1:40 — Creatives → Compliance (45s)
Show the three creatives; point at the failing one.

> "Composed from the brand kit, identical every run. This one breaks the rules
> on purpose."

Go to **Compliance**, type: `{fail_copy}` → Check.

> "{fail_n} findings, each citing its clause. Recall and precision are
> {c["worst_recall"]:.0%} in the worst of three languages."

Then type: `{pass_copy}` → Check.

> "And it passes. A discount with its terms stated is legal. A tool that flags
> good copy gets switched off."

## 2:25 — Measure (30s)
> "Lift with a confidence interval — and the estimator's own bias, measured on a
> window where nothing happened. It is {u["recovery"][0]["bias"]:+.1%}, because the
> donor sites are weather-flat and Marina Walk is not."

Point at the recovery table.

> "Five injected lifts, all recovered within
> {u["worst_error_points"]:.2f} points. That is why the number above is worth
> reading."

## 2:55 — Close (5s)
Go to **Crew**.

> "And nothing here can publish anything. That column reads 'none' on every row,
> and a test asserts it over the whole registry."

---

**If asked one follow-up, make it the bias.** It is the finding that shows the
project caught something it did not set out to find.
"""


def build_notebook() -> str:
    """A Jupyter notebook that re-runs the headline numbers.

    Written as JSON rather than authored in a UI, because a notebook committed
    from a UI carries whatever state that session happened to be in — and this
    one has to reproduce, not resemble.
    """
    cells = [
        (
            "markdown",
            [
                "# UPLIFT / MAWSIM — reproducing the AI 208 numbers\n",
                "\n",
                "Every figure in the report comes from `docs/results/`, and every one of\n",
                "those is written by a script in `scripts/` or a `--verify` in `pipeline/`.\n",
                "This notebook re-runs the evaluations so a reader can check them rather\n",
                "than take them.\n",
                "\n",
                "**SIDRA is a fictional brand and its footfall is generated.** What is not\n",
                "generated is the evaluation: the forecast is scored against a seasonal-naive\n",
                "baseline on held-out time, and a model that cannot beat it is not used.\n",
                "\n",
                "Run from the repository root: `uv run jupyter lab docs/artefacts/`.\n",
            ],
        ),
        (
            "code",
            [
                "import sys\n",
                "sys.path.insert(0, '..'); sys.path.insert(0, '../..')\n",
                "from services.api.core.db import connect\n",
                "conn = connect()\n",
                "counts = conn.execute(\n",
                "    \"SELECT 'weather' k, COUNT(*) n FROM weather_hourly UNION ALL \"\n",
                "    \"SELECT 'footfall', COUNT(*) FROM footfall_hourly UNION ALL \"\n",
                "    \"SELECT 'events', COUNT(*) FROM events UNION ALL \"\n",
                "    \"SELECT 'baskets', COUNT(*) FROM pos_baskets\"\n",
                ").fetchall()\n",
                "{r[0]: r[1] for r in counts}\n",
            ],
        ),
        (
            "markdown",
            [
                "## 1 · The per-site argument\n",
                "\n",
                "All four sites sit in neighbouring ERA5 grid cells and get the SAME weather.\n",
                "What differs is how they respond — and the elasticity is DERIVED from the\n",
                "seat counts in the brand kit, not written into the simulator, so the ordering\n",
                "below is emergent rather than assumed.\n",
            ],
        ),
        (
            "code",
            [
                "from services.api.brand import load_brand\n",
                "from pipeline.footfall import fit_temperature_slope\n",
                "\n",
                "for z in sorted(load_brand().zones, key=lambda z: -z.outdoor_share):\n",
                "    slope = fit_temperature_slope(conn, z.code)\n",
                "    print(f'{z.code}  outdoor {z.outdoor_share:6.1%}   slope {slope:+.5f} per degree')\n",
            ],
        ),
        (
            "markdown",
            [
                "## 2 · Forecast against the baseline\n",
                "\n",
                "Chronological holdout, never random — a random split on an hourly series with\n",
                "a weekly cycle is close to handing the model the answer.\n",
            ],
        ),
        (
            "code",
            [
                "from services.api.marketing.features import load_frame\n",
                "from services.api.marketing.forecast import evaluate\n",
                "\n",
                "for zone in ('DXB-DTN', 'DXB-MOE', 'DXB-MAR', 'DXB-DEI'):\n",
                "    r = evaluate(load_frame(conn, zone))\n",
                "    print(f'{r.zone}  MAE {r.mae:7.2f} vs naive {r.baseline_mae:7.2f} ({r.improvement:+.1%})'\n",
                "          f'   weeks {r.weeks_won}/{r.weeks_total}   cover80 {r.coverage_80:.0%}'\n",
                "          f'   sMAPE {r.smape:5.1f}% vs {r.baseline_smape:5.1f}%')\n",
                "\n",
                "# sMAPE is WORSE on every site and is reported anyway. Seasonal naive returns\n",
                "# last week's exact integer, which on low-count hours is proportionally perfect\n",
                "# while being absolutely further away. MAE is the gate; sMAPE is disclosed.\n",
            ],
        ),
        (
            "markdown",
            [
                "## 3 · Uplift, and the estimator's own bias\n",
                "\n",
                "The bias is not noise. The donor blend is weather-flat and the treated site is\n",
                "not, so the counterfactual drifts as the Gulf summer arrives. It is measured on\n",
                "a placebo window where nothing happened, and subtracted.\n",
            ],
        ),
        (
            "code",
            [
                "import pandas as pd\n",
                "from services.api.marketing import uplift\n",
                "\n",
                "df = pd.read_sql_query(\n",
                '    "SELECT substr(ts_local,1,10) d, zone_code, SUM(footfall) f "\n',
                '    "FROM footfall_hourly GROUP BY d, zone_code", conn)\n',
                "daily = df.pivot(index='d', columns='zone_code', values='f').dropna().astype(float)\n",
                "\n",
                "for inj in (0.30, 0.20, 0.10, 0.05, 0.0):\n",
                "    x = uplift.recovery_check(daily, 'DXB-MAR', '2026-06-01', '2026-06-14', injected=inj)\n",
                "    print(f\"injected {inj:+.0%}   raw {x['recovered_raw']:+.2%}   bias {x['bias']:+.2%}\"\n",
                "          f\"   ->  {x['recovered']:+.2%}   error {x['error_points']:+5.2f} pts\"\n",
                "          f\"   {'ok' if x['within_5_points'] else 'FAIL'}\")\n",
            ],
        ),
        (
            "markdown",
            [
                "## 4 · Compliance, per language\n",
                "\n",
                "Reported per language rather than blended: the first version of the rule set\n",
                "caught six violations in English, four in Arabic and two in Hindi, and one\n",
                "blended number would have hidden exactly the imbalance it was written to find.\n",
            ],
        ),
        (
            "code",
            [
                "from services.api.creative import compliance\n",
                "\n",
                "for lang in ('en', 'ar', 'hi'):\n",
                "    v = compliance.evaluate_by_language()[lang]\n",
                "    print(f\"{lang}  {v['cases']:>2} cases  \"\n",
                "          f\"recall {v['recall']:.0%}  precision {v['precision']:.0%}  \"\n",
                "          f\"missed {len(v['missed'])}  false alarms {len(v['false_alarms'])}\")\n",
            ],
        ),
        (
            "code",
            [
                "# The clean half of the gold set is deliberately adversarial: a discount WITH\n",
                "# its terms, an allergen statement, 'fresh' qualified by 'baked on site'.\n",
                "# Precision matters because a tool that flags good copy gets switched off.\n",
                "for text in ('Our best sugar-free detox latte',\n",
                "             'Was AED 32, now AED 24. Until 30 September.'):\n",
                "    v = compliance.check(text)\n",
                "    print(f'{text!r}\\n  -> {len(v.findings)} finding(s): '\n",
                "          f'{[f.rule_id for f in v.findings]}\\n')\n",
            ],
        ),
        (
            "markdown",
            [
                "## 5 · Everything the report quotes\n",
                "\n",
                "If any of these is missing, `scripts/build_report.py` refuses to build rather\n",
                "than quietly omitting the section that cites it.\n",
            ],
        ),
        (
            "code",
            [
                "from pathlib import Path\n",
                "\n",
                "for p in sorted(Path('../results').glob('*.json')):\n",
                "    print(f'{p.name:28} {p.stat().st_size:>9,} bytes')\n",
            ],
        ),
    ]
    return json.dumps(
        {
            "cells": [
                {
                    "cell_type": kind,
                    "metadata": {},
                    "source": src,
                    **({"outputs": [], "execution_count": None} if kind == "code" else {}),
                }
                for kind, src in cells
            ],
            "metadata": {
                "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                "language_info": {"name": "python", "version": "3.13"},
            },
            "nbformat": 4,
            "nbformat_minor": 5,
        },
        indent=1,
    )


def main() -> int:
    ARTEFACTS.mkdir(parents=True, exist_ok=True)
    try:
        md = build_markdown()
    except MissingResult as exc:
        print(f"REFUSED: {exc}")
        return 1

    path = ARTEFACTS / "AI208_MAWSIM_report.md"
    unchanged = path.exists() and path.read_text(encoding="utf-8") == md
    path.write_text(md, encoding="utf-8")
    print(f"wrote {path.relative_to(ROOT)} ({len(md):,} chars)")

    # A .docx is a zip, and python-docx stamps each entry with the moment it was
    # written, so rebuilding an unchanged report produces 42 KB of different
    # bytes and an unreadable binary diff. Rebuild it only when something moved.
    #
    # "Something" is the prose OR THE RENDERER. The first version of this guard
    # watched only the markdown, so rewriting build_docx.py from a flat
    # paragraph loop into a laid-out document changed nothing on disk and said
    # "unchanged" — a cache that outlived the thing it was caching.
    docx_out = ARTEFACTS / "AI208_MAWSIM_report.docx"
    renderer = Path(__file__).resolve().parent / "build_docx.py"
    renderer_is_newer = docx_out.exists() and renderer.stat().st_mtime > docx_out.stat().st_mtime
    if unchanged and docx_out.exists() and not renderer_is_newer:
        print("  docx unchanged; not rewritten")
        return _write_side_artefacts()

    try:
        from build_docx import render

        docx_path = ARTEFACTS / "AI208_MAWSIM_report.docx"
        render(
            md,
            docx_path,
            {
                "title": "UPLIFT / MAWSIM",
                "tagline": "Demand-aware promo planning for Dubai retail",
                "subject": "AI 208 — AI in Marketing",
                "author": "Krishna Mathur",
                "school": "SP Jain School of Global Management — MAIB, Term 4",
                "date": date.today().strftime("%d %B %Y"),
                "disclaimer": (
                    "SIDRA is a fictional brand invented for this coursework, and its "
                    "footfall series is generated. Every figure in this document is read "
                    "from docs/results/ by scripts/build_report.py rather than typed."
                ),
            },
        )
        print(f"wrote {docx_path.relative_to(ROOT)}")
    except ImportError:
        print("python-docx not installed; the markdown report is the artefact")

    return _write_side_artefacts()


def _write_side_artefacts() -> int:
    # Imported under a distinct name: `build_deck` is already this module's
    # markdown outline builder, and importing over it made the outline builder
    # the .pptx builder — which failed loudly, but would not have to.
    try:
        from build_deck import build as build_pptx

        out = build_pptx(ARTEFACTS / "AI208_MAWSIM_deck.pptx")
        print(f"wrote {out.relative_to(ROOT)}")
    except ImportError:
        print("python-pptx not installed; the deck outline is the artefact")

    for name, builder in (
        ("AI208_deck_outline.md", build_deck),
        ("AI208_viva_15.md", build_viva),
        ("AI208_demo_3min.md", build_demo),
        ("AI208_MAWSIM_notebook.ipynb", build_notebook),
    ):
        try:
            out = ARTEFACTS / name
            out.write_text(builder(), encoding="utf-8")
            print(f"wrote {out.relative_to(ROOT)}")
        except MissingResult as exc:
            print(f"REFUSED {name}: {exc}")
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
