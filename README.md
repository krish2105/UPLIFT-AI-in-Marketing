# UPLIFT — MAWSIM

**Demand-aware promo planning for Dubai retail.** Events, weather, holidays and
school calendars drive footfall. MAWSIM forecasts that demand per store zone,
lets a bounded agent crew plan promotions and creatives against the forecast,
checks every claim against brand and food-advertising rules with citations, and
then measures **incremental lift** rather than clicks.

Built for SP Jain MAIB Term 4, AI 208 AI in Marketing. Owner: Krishna Mathur.

> ### The brand is fictional
> **SIDRA** (سدرة) is an invented Dubai speciality coffee and bakery chain with
> four locations. It is not a real company, and nothing here is a claim about any
> real business. The footfall and point-of-sale figures it is planned against are
> **generated** by a seeded model in `pipeline/footfall.py`. `FootfallRecord`
> cannot be constructed without `simulated=True`, the database column is
> `NOT NULL CHECK (simulated = 1)`, and every API response and every chart says
> so. A real pilot replaces that dataset with an actual export; nothing else in
> the system changes.

![The Season tab in the night register: the daypart dial, the mashrabiya
confidence screen, eight weeks of demand for four sites, and evening footfall
plotted against apparent temperature](docs/images/season-night.png)

**The chart on the lower right is the argument.** Four sites, one axis, evening
footfall against apparent temperature. Marina Walk — 54% of its seats outdoors —
falls away as the evening heats up. Al Barsha, fully enclosed, barely moves. All
four sit in neighbouring ERA5 grid cells, so they get the *same* weather: what
differs is how they respond to it, and that is why demand is forecast per site
rather than per brand.

That elasticity is not written into the simulator. It is **derived** from the
seat counts in `data/brand/sidra.yaml`, so the measured result — Marina Walk
2.4× more temperature-sensitive than Al Barsha, with the ordering across all
four sites matching their outdoor share exactly — is emergent rather than
assumed. Change the seat counts and it follows.

<table>
<tr>
<td width="50%"><img src="docs/images/data-night.png" alt="The Data tab: five datasets, each with its label, licence, source and the date it was verified"></td>
<td width="50%"><img src="docs/images/brand-day.png" alt="The Brand tab in the day register: four SIDRA sites with their outdoor seating share drawn as a bar"></td>
</tr>
<tr>
<td><b>Every dataset says what it is.</b> Observed, curated, simulated or
sample — a Dataset cannot be constructed without a licence, a source URL, a
named build script and one of those four labels. The constructor raises, and a
test asserts each refusal, so a dataset added later without provenance fails the
build rather than appearing on a chart with nothing attached to it.</td>
<td><b>The brand kit is the single source of truth.</b> The guideline PDF, the
Creative agent's palette and the Compliance agent's eleven rules all read
<code>data/brand/sidra.yaml</code>, so the document a reviewer checks and the
rules the system applies cannot drift apart.</td>
</tr>
</table>

> Captured from a local run against a built database. Regenerate with
> `cd apps/web && node scripts/screenshots.mjs`.

## Standing constraints

- **Zero paid inference.** Ollama (local) → Gemini free tier → Groq free tier →
  a deterministic stub. Anthropic is present in the provider chain and
  permanently refuses to serve, so the refusal is visible in the code and covered
  by a test rather than being an absence someone later "fixes". Budgets are
  counted in **requests**, never tokens: the free tiers do not return
  trustworthy token accounting, and a number the project cannot verify has no
  business appearing in a report.
- **Only free, licensed data.** Every source is in
  [`docs/datasets.md`](docs/datasets.md) with its URL, the date it was verified
  **by fetching it**, and its licence. The sources that refused are recorded
  there as prominently as the ones that worked, because which sources refused is
  part of what shaped the design.
- **Every number traces to [`docs/results/`](docs/results).** Not as a promise —
  `tests/test_docs_match_results.py` extracts the figures quoted in
  `docs/models.md` and fails if they disagree with the JSON that produced them.
- **No agent has a side-effect tool.** Nothing is published or executed
  externally. Exporting a campaign is a human action, taken outside this
  application.

## What is measured, and where

| Claim | Evidence | Result |
|---|---|---|
| Weather history is complete | `python -m pipeline.weather --verify` | 18,048 hours per site, no gap over 3 h — [`A4`](docs/results/A4-weather-etl.json) |
| Islamic dates reproduce UAE observances | `python -m pipeline.calendar --verify` | all four 2025 observances matched — [`A5`](docs/results/A5-calendar.json) |
| Events are curated and say so | `python -m pipeline.events --verify` | 245 instances, no row claiming a verified date — [`A6`](docs/results/A6-events.json) |
| Sites respond differently to weather | `python -m pipeline.footfall --verify` | slope ordering matches outdoor-share ordering — [`A7`](docs/results/A7-footfall.json) |
| The embedding model is fit for trilingual retrieval | `python scripts/spike_embeddings.py` | bge-m3 +0.447/+0.318 margin; nomic-embed-text disqualified — [`A9`](docs/results/A9-embedding-spike.json) |
| Text and UI meet WCAG in both registers | `node apps/web/scripts/check-contrast.mjs` | 34 pairs measured — [`A2`](docs/results/A2-contrast.json) |
| Chart series are distinguishable | `node apps/web/scripts/check-palette.mjs` | six checks, both registers — [`A10`](docs/results/A10-palette.json) |
| The shell is responsive, accessible and RTL-correct | `make e2e` | 35 Playwright tests |

## Running it

```bash
uv sync --extra dev
cd apps/web && npm install && cd ../..
make etl        # build the datasets — weather and events reach the network, cached to data/raw/
make check      # the green bar: ruff, pytest, contrast, palette, placeholders, typecheck
make e2e        # Playwright; starts both servers itself
make api        # http://localhost:8000/docs
make web        # http://localhost:3000
```

## Layout

| Path | What lives there |
|---|---|
| `services/api/` | FastAPI service: dataset registry, series endpoints, brand kit loader |
| `pipeline/` | The four ETLs — weather, calendar, events, footfall — each with `--verify` |
| `apps/web/` | Next 16 application: fifteen tabs, three languages, two registers |
| `data/brand/sidra.yaml` | The single source of truth for the fictional brand |
| `docs/results/` | Every measured number, written by a script |
| `docs/datasets.md` · `docs/models.md` | What the data is, what the models are, and why |
| `docs/directions.md` | The three design directions that were built, and which one was chosen |

## Limitations

Stated here rather than discovered by a reader.

- **Footfall is generated.** No public hourly footfall series exists for any
  Dubai café. What is not invented is the evaluation: the forecaster is scored
  against a seasonal-naive baseline on held-out data, and a model that cannot
  beat "same hour last week" is not used.
- **Event dates are placed, not confirmed.** Visit Dubai returns 403 to every
  non-browser client and no redistributable feed exists. The series, venues and
  calendar windows are real; the dates of a given edition sit inside the
  established window and carry `date_confidence: annual_window`.
- **Islamic holidays are calculated.** u.ae states they are set by moon
  sighting, so every such row carries one day of uncertainty.
- **School breaks are approximate windows.** KHDA's calendar page redirects to a
  host whose certificate does not verify.
- **Most compliance clauses are unread.** The source documents are verified; the
  specific clauses are quoted verbatim during Phase C's corpus ingestion, and
  until then the generated brand PDF prints "clause unverified" rather than
  implying otherwise.
- **Weather is a coarse grid.** ERA5 at roughly 11 km, so the four sites do not
  each get their own station.

## Not advice

MAWSIM produces a marketing plan and a compliance opinion for a fictional brand
as coursework. It is not legal advice, not regulatory clearance, and not a
substitute for real customer research. Its persona panel simulates reactions; it
does not observe them.
