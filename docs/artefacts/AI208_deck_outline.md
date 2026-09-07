# AI 208 — UPLIFT / MAWSIM · deck outline

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
What differs is how they respond. Marina Walk is 53% outdoor; Al Barsha
is fully enclosed. **The fitted slopes order exactly by outdoor share.**
**Visual:** evening footfall against apparent temperature, four lines.

## 4 · The data, and what each part of it is
Five datasets, four provenance labels: observed, curated, simulated, sample.
A Dataset cannot be constructed without a licence and a label.
**Visual:** the Data tab.

## 5 · Forecast
Gradient boosting with exogenous drivers, chronological holdout.
**36 of 36 site-weeks beaten** against a 70%
target; MAE 28%–34% below seasonal naive.
**Visual:** the week-by-week table.

## 6 · Where the model is worse, and why we say so
sMAPE is higher than the baseline on every site. Seasonal naive returns the
exact integer from last week, which on low-count hours is proportionally perfect
while being absolutely further away. MAE is the gate; sMAPE is reported.
**This slide is the one that earns the rest.**

## 7 · Segments and allocation
RFM at **92%** bootstrap stability; a concave
channel × daypart allocator whose optimum is checkable (equal marginal return).
Elasticities are assumed, and every response says so.
**Visual:** the 15-cell heat table.

## 8 · Creatives and compliance
Composed from the brand kit, identical every run. 11 rules, each citing its
clause. Recall and precision **100%** in the worst of three languages.
**Visual:** the `summer-detox` creative with its
6 findings.

## 9 · Measurement
Synthetic control + CUPED. An injected lift is recovered within
**2.61 points** of a five-point tolerance.
**Visual:** treated against counterfactual.

## 10 · The estimator's own bias
It returns -3.5% where nothing happened, because the donor blend is
weather-flat and the treated site is not. Measured on a placebo window and
subtracted, with both numbers reported.
**The second slide that earns the rest.**

## 11 · Safety, and the attack that used to work
No agent has a tool that reaches the outside world; the whole API is GET.
**48/48** red-team attacks held across 7
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
