# UPLIFT / MAWSIM — AI 208 report

**Demand-aware promo planning for Dubai retail.**
SP Jain MAIB Term 4 · AI 208 AI in Marketing · Krishna Mathur
Generated 2026-09-07 from `docs/results/` by `scripts/build_report.py`.

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
| Method | GradientBoostingRegressor with absolute-error loss for the median and pinball loss at the 10th and 90th percentiles for the interval. Chronological holdout of 56 days; the baseline is seasonal naive — the same hour, same weekday, last week. |
| Baseline | Seasonal naive — same hour, same weekday, last week |
| Result | **36 of 36 site-weeks beaten** (100%) against a 70% target |

| Site | MAE | Baseline MAE | Improvement | 80% coverage |
|---|---:|---:|---:|---:|
| DXB-DTN | 7.84 | 11.18 | +29.9% | 91% |
| DXB-MOE | 9.15 | 13.92 | +34.3% | 91% |
| DXB-MAR | 8.46 | 11.75 | +28.0% | 93% |
| DXB-DEI | 4.55 | 6.39 | +28.7% | 91% |

Best absolute error: **DXB-DEI at 4.55**.

### What the model gets wrong, and why it is reported

sMAPE is higher for the model than for the baseline on every site, and MAE is lower. Both are correct. Seasonal naive returns the exact integer count from the same hour last week, which on the many low-count hours is often exactly right and therefore proportionally perfect, while being further away in absolute terms. For staffing a cafe the absolute error is the decision-relevant one, so MAE is the gate and sMAPE is reported rather than optimised.

## 3. Incrementality

| | |
|---|---|
| Method | Synthetic control with non-negative weights summing to one, fitted on 56 pre-period days; CUPED variance reduction; a permutation placebo across donor sites for the p-value; and a placebo-in-time run for the estimator's own bias. |
| Tolerance | 5 percentage points |
| Result | **all 5 recovery checks inside tolerance**, worst error 2.61 points |

| Injected | Raw | Bias | Adjusted | Error |
|---:|---:|---:|---:|---:|
| +30% | +23.91% | -3.48% | +27.39% | -2.61 pts |
| +20% | +14.38% | -3.48% | +17.86% | -2.14 pts |
| +10% | +4.85% | -3.48% | +8.33% | -1.67 pts |
| +5% | +0.08% | -3.48% | +3.56% | -1.44 pts |
| +0% | -4.68% | -3.48% | -1.20% | -1.20 pts |

### The estimator's own bias

The estimator returns about -3.5% on a window where nothing happened, and that is not noise. The donor blend is dominated by Al Barsha, which is fully enclosed; Marina Walk is more than half outdoor seating. As the Gulf summer arrives Marina falls away from its own history while the enclosed donor does not, so the counterfactual drifts above the treated site for reasons unrelated to any promotion. With four sites and one of them uniquely weather-elastic, no convex blend of the others can match Marina's weather response: it is inside the donors' hull on level and outside it on elasticity. That is a real limitation of synthetic control on a small donor pool, so it is measured on a placebo window and subtracted, and both numbers are reported.

## 4. Segmentation

RFM quintiles over the point-of-sale sample, assigned by a decision list so the rules read in order rather than as overlapping sets. Stability is the share of customers keeping their segment across 25 bootstrap resamples.

| | |
|---|---|
| Customers | 1,854 |
| Bootstrap stability | **91.8%** keep their segment across 25 resamples |

| Segment | Customers | Revenue share | Customer share |
|---|---:|---:|---:|
| Champions | 485 | 58.3% | 26.2% |
| Loyal | 257 | 17.7% | 13.9% |
| Hibernating | 497 | 7.6% | 26.8% |
| Promising | 225 | 4.9% | 12.1% |
| At risk | 147 | 4.6% | 7.9% |
| Occasional | 188 | 4.1% | 10.1% |
| Big spenders | 55 | 2.8% | 3.0% |

The response ceilings and saturation rates are structural assumptions, not fitted values: no promotion has run, so there is nothing to fit them to. Phase D's measured lift replaces them.

## 5. Media allocation

Fifteen cells — five channels by three dayparts — each with a saturating response a(1-exp(-bx)). The objective is concave, so greedy marginal allocation reaches the exact optimum and the KKT condition (equal marginal return across funded cells) is checkable.

Ninety-day daypart demand: evening 242,655, midday 103,356, morning 111,317

| Budget | Incremental visits | Per 1,000 AED |
|---:|---:|---:|
| 2,000 | 571 | 285.7 |
| 4,000 | 918 | 229.4 |
| 6,000 | 1,186 | 197.7 |
| 8,000 | 1,409 | 176.1 |
| 12,000 | 1,765 | 147.1 |
| 16,000 | 2,039 | 127.4 |
| 24,000 | 2,444 | 101.8 |
| 32,000 | 2,727 | 85.2 |

Affinities and saturation rates are structural assumptions scaled by the forecast, not fitted elasticities. No promotion has run. Every response the allocator returns carries assumed=true, and an allocator presented as optimal on invented elasticities would be the most confident wrong thing in this application.

## 6. Brand and legal compliance

| | |
|---|---|
| Method | Regex over NFKC-normalised text against the eleven rules in data/brand/sidra.yaml. Deterministic: a rule engine whose verdict depends on a model's mood cannot be audited. Three rule types — pattern, conditional (fires unless a qualifier is present) and presence (fires on something missing, such as an allergen statement). |
| Target recall | 90% |
| Worst recall across languages | **100%** |

| Language | Cases | Recall | Precision |
|---|---:|---:|---:|
| en | 40 | 100% | 100% |
| ar | 10 | 100% | 100% |
| hi | 10 | 100% | 100% |

Recall is reported per language and never blended. The rule set was written in English first and on the same violating creative caught six rules in English, four in Arabic and two in Hindi — for a UAE brand a real gap rather than a cosmetic one. Arabic and Hindi patterns were added and the gold set extended; a single blended number would have hidden the imbalance it was written to find.

Precision is reported beside recall because a rule that flags everything scores perfect recall. The clean half of the gold set is deliberately adversarial: it contains discounts with stated terms, allergen statements, and the word 'fresh' qualified by 'baked on site'.

## 7. Retrieval

Embedding model chosen by measurement, not preference. The property that matters
is the **margin over an unrelated control** — a raw similarity between a sentence
and its translation is high under almost any model and means nothing alone.

| Model | dim | Worst HI margin | Worst AR margin | Verdict |
|---|---:|---:|---:|---|
| bge-m3:567m | 1024 | +0.447 | +0.318 | local choice |
| nomic-embed-text | 768 | -0.076 | -0.127 | **disqualified** |

`nomic-embed-text` is not weaker here — it is wrong. Its margin is negative: on
the nutrition probe it scores an English sentence about espresso-machine
depreciation above the Hindi and Arabic translations of the sugar-free rule.
Asked in Arabic what the threshold is, a system using it would return the
accounting sentence with a citation attached.

## 8. Accessibility and colour

| | |
|---|---|
| Contrast pairs measured | 36, both registers |
| Palette checks | seven, both registers |

The palette was rejected twice by its own gate before passing: a saturated
midday hue collapsed to ΔE 3.5 under deuteranopia, and desaturating it made it
read grey. Neither failure is visible by eye on a designer's monitor.

## 9. Targets

| Target | Result | |
|---|---|---|
| Forecast beats naive on ≥70% of weeks | 100% | MET |
| Uplift recovery within ±5 points | worst 2.61 pts | MET |
| Compliance recall ≥0.90 | 100% worst language | MET |
| Segments stable under bootstrap | 91.8% | MET |

## 10. Safety, and what happened when it was attacked

No agent in the registry holds a tool with a side effect; the whole API is GET,
so there is no verb with which to write. That is an architectural claim, and a
claim is worth what the attempt to break it is worth.

`scripts/red_team.py` makes 34 attempts across
7 OWASP ASI controls — prompt injection into the
compliance checker, script-mixing and zero-width evasion of the claim rules,
forged Admin headers, HTTP verbs the API does not answer, provenance stripping,
and budget exhaustion. **33 of 34 held.**

| Control | Attempts | Held |
|---|---|---|
| ASI-01 | 5 | 5 |
| ASI-03 | 13 | 13 |
| ASI-04 | 2 | 2 |
| ASI-06 | 5 | 5 |
| ASI-07 | 2 | 2 |
| ASI-08 | 1 | 1 |
| ASI-09 | 6 | 5 |

One case is recorded as a break on purpose. RT-AUT-06 BREAKS, and the scoreboard says so. The Admin role is an unauthenticated request header, so 'ADMIN ' is normalised, accepted, and sendable by anyone; the attacker engages the kill switch without holding the scope. The project accepts that risk — the header is a coursework stand-in for identity and /admin/roles states it in the UI — but an accepted risk is still a break. Scoring it as held would have made the harness report 34/34 while a forged header worked, which is precisely the reassurance it exists to withhold. Binding roles to identity is the fix, and it is listed under limitations rather than claimed.

A pass here is narrow, and the file says so in its own words:
The attack did not achieve its objective. It does not mean the system is secure — no harness can say that. It means these specific attempts, the ones a marketing-compliance tool actually invites, were tried and recorded, and the result is a number rather than an assurance.

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
- **Roles are a request header, not an identity.** `X-Mawsim-Role: admin` is
  unauthenticated and therefore forgeable, and the red team scores that as a
  break rather than an expected result. Binding roles to a signed session is the
  fix; the application states the gap at `/admin/roles` instead of implying a
  control it does not have.
- **The persona panel is not customer research.** It applies a rubric; it does
  not observe a reaction.
- **Synthetic control cannot fully control for weather here.** With four sites
  and one uniquely weather-elastic, the treated unit is inside the donors' hull
  on level and outside it on elasticity.

## Not advice

This produces a marketing plan and a compliance opinion for a fictional brand as
coursework. It is not legal advice, not regulatory clearance, and not a
substitute for real customer research.
