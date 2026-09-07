# Models

Every model UPLIFT uses, why it was chosen, and the measurement behind the
choice. **No number on this page was typed from memory** — each comes from a
script in `scripts/` that writes to `docs/results/`, and
`tests/test_docs_match_results.py` fails if this page and that file ever
disagree.

**Standing constraint: zero paid inference.** Every model below is either local
(Ollama, on the owner's machine) or a documented free tier. Anthropic is present
in the provider chain and permanently refuses to serve; that refusal is covered
by a test rather than by a comment.

---

## Embeddings

**Decision: `bge-m3:567m` locally, `paraphrase-multilingual-MiniLM-L12-v2` when deployed.**

Measured by `scripts/spike_embeddings.py` on 2026-09-07 →
[`docs/results/A9-embedding-spike.json`](results/A9-embedding-spike.json).

### What was measured, and why it is not raw similarity

UPLIFT answers questions in English, Hindi and Arabic against one corpus — the
SIDRA brand guidelines, Codex nutrition-claim guidance, UAE consumer-protection
guidance, event listings. An Arabic question has to retrieve the English clause
that answers it.

A raw similarity between a sentence and its translation is high for almost any
model and tells you nothing. What tells you something is the **margin over an
unrelated control**: how much closer the model puts a translation than it puts a
sentence about something else. Three probes drawn from the actual corpus were
each scored against three controls taken from the *same business* — depreciation
policy, a compliance verdict, aggregator commission — because an easy control
inflates every margin and would make a bad model look usable. The reported
margin is against the **hardest** control, so a model only passes if its worst
case passes.

Bar: **margin ≥ 0.25** on both the Hindi and the Arabic pair, on every probe.

### Results

| Model | Backend | dim | worst margin HI | worst margin AR | Verdict |
|---|---|---:|---:|---:|:--|
| **bge-m3:567m** | Ollama | 1024 | **+0.447** | **+0.318** | usable — local choice |
| nomic-embed-text | Ollama | 768 | −0.076 | −0.127 | **disqualified** |
| **paraphrase-multilingual-MiniLM-L12-v2** | fastembed ONNX | 384 | **+0.565** | **+0.579** | usable — deployed choice |
| paraphrase-multilingual-mpnet-base-v2 | fastembed ONNX | 768 | +0.627 | +0.578 | usable, too large to deploy |

### `nomic-embed-text` is not weak here — it is wrong

Its margin is **negative** on the nutrition-claim probe: it scores the English
sentence about *espresso machine depreciation* at 0.528 against the Hindi
translation of the sugar-free rule at 0.452 and the Arabic at 0.401.

Put plainly: asked in Arabic what the sugar-free threshold is, a system using
this model would rank an accounting sentence above the answer, and return it
with a citation attached. A confidently wrong answer carrying provenance is
worse than no answer, so this model is **disqualified rather than
deprioritised**. The spike script asserts it stays disqualified; if it ever
clears the bar, this page needs revisiting rather than quietly updating.

### The larger margin did not win the local slot

MiniLM's worst margin (+0.565 / +0.579) is *better* than bge-m3's (+0.447 /
+0.318), and it is still not the local model. Context window is why: bge-m3
takes 8192 tokens against MiniLM's 128. On a four-sentence probe that costs
nothing; on a page of the brand-guidelines PDF it means chunks an order of
magnitude smaller and far more of them, which fragments exactly the clauses the
Compliance agent has to cite whole. bge-m3 stays local because local is where
documents are actually read.

mpnet has the best margins of all and is 1.0 GB. The deployed instance is a
512 MB Render free dyno, so it is measured for comparison and not used.

---

## Retrieval: what the embeddings are actually allowed to do

The A9 spike chose `bge-m3` on cross-lingual margin and the architecture named
`sqlite-vec`. Neither settles the question that matters at request time: **may a
passage enter an answer on similarity alone?** `scripts/spike_retrieval.py`
measured it, because a threshold nobody measured is a threshold set to whatever
made the demo work.

Eight in-domain questions across three languages, ten fluent out-of-domain ones
aimed at the same tool — "send me the invoice", "when is the next board
meeting" — scored against the 39-passage corpus.

| | similarity |
|---|---|
| worst in-domain question | **0.4577** |
| best out-of-domain question | **0.6272** |

The impostor outscores every real question but one. There is no separating
threshold, and the overlap is not marginal — so **embeddings do not admit
anything**. Admission is lexical: a passage enters because the query's own words
are in it, and cosine then re-ranks what the words already found. The bar sits at
0.647, above all but one genuine question, which is the measurement
saying the same thing in the code's own terms.

End to end that is **6 of 8**
in-domain questions answered and **10 of
10** out-of-domain questions refused. The two losses are
the Arabic and Hindi questions about *weather*, and the cause is content rather
than retrieval: the zone and dataset passages are English prose, so the only
non-Latin tokens in the corpus are the regex triggers inside the claim rules. A
non-English question about a RULE lands; one about the DATA has nothing in its
own script to land on. Translating those passages fixes it. Lowering the bar
would also fix it, and would ship an invoice request as a cited answer.

**`sqlite-vec` was removed rather than adopted.** It was a dependency from the
first commit and was never imported — the most common way a dependency lies, by
naming an intention rather than a fact. Its value is approximate nearest
neighbours over a corpus too large to scan; this corpus is
39 passages, where an ANN index is slower than the scan it
replaces and exists to make the architecture diagram look right. Exact cosine
over a small matrix is what runs. `corpus.search()` is the only function that
changes if the corpus ever reaches the tens of thousands.

## Chat

**Decision: `qwen3:4b-instruct` for volume, `qwen3:8b` for judgement, locally.
Gemini free → Groq free → a deterministic stub when deployed.**

| Role | Model | Why |
|---|---|---|
| Creative variants, persona panel | `qwen3:4b-instruct` | High call volume — three variants × three languages × five personas is sixty-odd calls per slot. Measured at **3.3 s** for a schema-constrained JSON reply, which makes that affordable. |
| Planner, Compliance, Auditor | `qwen3:8b` | Judgement over a retrieved corpus, where a wrong answer is expensive and the call count is low. |
| Creative compliance re-read | `qwen2.5vl:7b` | Reads the *rendered* creative back and re-runs the claim rules on the text a viewer actually sees. Catches a claim that survives into an image. |
| Deployed | Gemini free → Groq free → stub | No Ollama exists on a Render dyno. The stub is terminal, deterministic and dependency-free, so the crew runtime, budgets and citation gates are exercised with no model at all. |

`think: false` and `keep_alive: 30m` on every Ollama call. Reasoning tokens
triple the wall clock for output a creative brief then has to discard, and
without `keep_alive` the chat and embedding models evict each other between a
retrieval and the turn that uses it, so every turn pays a cold load.

---

## Forecasting

**Decision: scikit-learn `GradientBoostingRegressor`, not Prophet.**

Two reasons, in order of weight:

1. **It has to deploy.** Prophet's build chain does not fit a free Render
   instance. A model that cannot run where the application runs is not a
   candidate, however good it is.
2. **It has to be defensible in a viva.** The interesting claim here is that
   *exogenous drivers* — event proximity, apparent temperature against a site's
   outdoor share, Ramadan, school breaks — move demand. A gradient-boosted model
   takes those as explicit features and lets their contribution be read off. A
   structural time-series model would fold them into components that are harder
   to attribute.

The baseline is **seasonal naive** — same hour, same weekday, last week. Phase B
reports the win rate against it per week, and a model that cannot beat it is not
used: a forecast that loses to "same as last week" is worse than no forecast,
because it looks like knowledge.

---

## Quotas

Counted as **requests, not tokens**. The free tiers UPLIFT runs on do not return
trustworthy token accounting, and a number the project cannot verify has no
business appearing in a report. A request count is exact, cheap, and the thing
the free tiers actually rate-limit on. Exhaustion degrades to the next provider
with the reason recorded; it never raises to the caller.
