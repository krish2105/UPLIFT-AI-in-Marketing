# AI 208 — viva preparation

Fifteen questions an examiner is likely to ask, and the honest answer to each.
Where a number appears it comes from `docs/results/`.

---

**1 · Your footfall data is invented. Why should I believe anything downstream?**
You should not believe the DATA. You should judge the METHOD, and the method is
evaluated against a baseline that sees the same invented data. The forecast beats
seasonal naive on 36 of 36 site-weeks; if the model
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

**6 · Your uplift estimator returns -3.5% on a window
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
from 0% to 30%, all recovered within 2.61 points of a
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
red team ran 13
injection and evasion attacks against it, including "ignore all previous
instructions", and all held — because there is nothing there to persuade.

**11 · How do you know the rule set is any good?**
A 40-case gold set whose CLEAN half is deliberately
adversarial: discounts with stated terms, allergen statements, "fresh" qualified
by "baked on site". Recall and precision are both 100%
in English, and both clear the 90% target in Arabic and Hindi.
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
sentence about espresso-machine depreciation at 0.5281 —
ABOVE the Hindi translation of the claim itself at 0.4521. Its worst
margins are -0.0760 on Hindi and
-0.1272 on Arabic, against a bar of +0.25. Asked in Arabic
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
