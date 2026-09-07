# UPLIFT — AI in Marketing (AI 208) · app codename MAWSIM

> **For agentic workers:** REQUIRED SUB-SKILLS: `superpowers:writing-plans` produced this;
> `superpowers:executing-plans` runs it **inline, no subagents** (owner's standing instruction —
> it overrides the ultracode workflow default). Frontend work additionally loads
> `premium-frontend` + `ui-ux-pro-max` + `frontend-design`. Checkbox syntax; every task green;
> one conventional commit per task ending with
> `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.

---

## Context

Dubai retail demand swings hard with events, weather, holidays and school calendars, yet
promotions are still planned on gut feel. UPLIFT forecasts demand per store zone, lets a bounded
agent crew plan promotions and creatives against that forecast, checks brand and legal compliance
with citations, and then measures **incremental lift** rather than clicks.

It is coursework for SP Jain MAIB Term 4, AI 208, and simultaneously a portfolio and job-search
artefact. That dual purpose sets the bar: every number must trace to `docs/results/`, every
factual sentence in a generated report must carry a citation, and the whole thing must run on
**zero paid inference**.

This repo is standalone. Patterns were **read** from `COUNSEL-Design-Thinking` and
`MISAR-AI-OPERATIONS` (the two Term 4 siblings that actually exist on disk — the plan's
"YIELDMAP"/"RAQIB" are these) and are **reimplemented here, never imported**.

**Owner decisions already taken (this session):**

| Decision | Choice |
|---|---|
| Fictional brand | **SIDRA** (سدرة) — specialty coffee & bakery, 4 Dubai locations |
| Visual direction | **Undecided — build all three, owner picks from a live page** (Task A2) |
| 3D centrepiece | **Both** — Demand Terrain primary, Dubai Map extrusion as a toggled variant |
| Creative visuals | **Best free tier**: deterministic brand-accurate compositions as the reproducible base + a genuinely working free image tier, cached to disk so a live demo never depends on a live call |

---

## The brand (fictional, and said so everywhere)

**SIDRA** — specialty coffee & bakery, founded 2019, four Dubai locations. Invented for this
demo. The README, the app footer, the generated report and the brand PDF all state this.

| Zone | Site | Why it behaves differently |
|---|---|---|
| `DXB-DTN` | Downtown / Dubai Mall | tourist-heavy, event-elastic, flat across the week |
| `DXB-MOE` | Al Barsha / Mall of the Emirates | resident family, indoor, weather-**in**elastic |
| `DXB-MAR` | Marina Walk | outdoor seating → weather-**elastic**, strong evening peak |
| `DXB-DEI` | Deira | value segment, Ramadan-heavy, early-morning peak |

Four zones with genuinely different elasticities is what makes a per-zone forecast and a budget
allocator meaningful rather than decorative.

**Answering the F&B trade-off the owner accepted.** Café promo budgets are small, so a
channel-only media allocator would have little to say. The allocator therefore optimises over
**channel × daypart** — 5 channels (Instagram, Google, delivery Aggregator, near-store OOH,
SMS/CRM) × 3 dayparts (morning 07–11, midday 11–17, evening 17–23). That is a 15-cell simplex
with real structure: aggregator spend pays back at midday and dies at 07:00, OOH only works
within walking distance of a zone. Richer than the beauty case, not poorer.

**Claims-to-avoid** (drives the Compliance agent, each mapped to a cited rule):
`sugar-free` · `keto` · `detox` · `immunity` · `superfood` · `clinically proven` · `cures/treats`
· `100% natural` · `fresh` (unsubstantiated) · `artisan` (unsubstantiated) · unqualified caffeine
claims · any nutrition claim without the allergen statement.

---

## Verified data sources — run live on 2026-09-07

| Source | Result | Decision |
|---|---|---|
| Open-Meteo **archive** (hourly, Dubai) | **200**, hourly arrays returned | ✅ primary weather history |
| Open-Meteo **forecast** (daily/hourly) | **200**, 41.9 °C for 2026-09-07 | ✅ primary weather forecast |
| Nager.Date UAE holidays | **204 No Content** — AE not covered | ❌ → fallback below |
| `holidays` PyPI (MIT) + `hijri-converter` | available | ✅ fallback, cross-checked against **u.ae** (200) |
| **visitdubai.com/en/whats-on** | **403** — CDN blocks non-browser clients | ❌ → **curated CSV**, exactly the master plan's named fallback |
| Wikipedia REST API (CC BY-SA 4.0) | **200** | ✅ enriches anchor events (DSF, GITEX, Eid…) |
| bayanat.ae (UAE open data) | **200** | ✅ secondary |
| dubaipulse.gov.ae · opendata.gov.ae · uaelegislation.gov.ae | 000 / 000 / 403 | ❌ recorded as unusable |
| KHDA (khda.gov.ae) | **200** | ✅ school term dates |
| MoEC consumer protection · Dubai Municipality · UAE Media Office | **200 / 200 / 200** | ✅ compliance corpus |
| FAO/WHO **Codex CAC/GL 23-1997** (nutrition & health claims) | **200** | ✅ primary compliance authority |
| EUR-Lex Reg. 1924/2006 · ASA CAP food rules | 202 / 200 | ✅ comparators, attributed |
| Footfall series | **No exported file exists** in `MISAR-AI-OPERATIONS` — its `services/api/core/forecast.py::generate_history` builds it in-process | ⚠️ **reimplement the pattern** (weekday effect × trend × Ramadan × lognormal noise) extended to hourly/per-zone/event-coupled. `simulated=true` on every row and every API response. |

Every row of this table lands in `docs/datasets.md` with URL, retrieval date and licence.

---

## Assumptions — models, quotas, 3D data

**Models** (`ollama list` on this machine, Apple M4 Pro / 24 GB, Ollama 0.33.2):
`qwen3:8b` · `qwen3:4b-instruct` · `qwen2.5vl:7b` · `bge-m3:567m` · `nomic-embed-text` · `llama3.2:3b`.

- **Chat, local:** `qwen3:4b-instruct` for high-volume tasks (creative variants, 5-persona panel)
  — measured **3.3 s** for a schema-constrained JSON reply; `qwen3:8b` for reasoning-heavy roles
  (Planner, Compliance, Auditor). `think:false`, `keep_alive:30m`.
- **Chat, deployed:** Gemini free → Groq free → deterministic **stub**. Anthropic present and
  hard-off, enforced by a test.
- **Embeddings:** provisionally `bge-m3:567m` (1024-dim; measured EN~AR cosine **0.6375** on a
  probe pair). **Not final** — Task A9 runs the spike with a control margin and writes the
  decision to `docs/models.md`. Deployed embedder is decided by the same spike; COUNSEL's
  render.yaml records that a 512 MB free instance **cannot** load a fastembed ONNX session, so
  the deployed path is Gemini embeddings or lexical-only, and `/healthz` says which.
- **Forecasting:** scikit-learn `GradientBoostingRegressor`, **not Prophet** — Prophet's build
  chain will not fit a free Render instance, and a gradient-boosted model with explicit exogenous
  features is more defensible in a viva. Baseline is seasonal-naive. Recorded in `docs/models.md`.
- **Vision:** `qwen2.5vl:7b` reads the *rendered* creative back and re-runs the claim rules on the
  visible text. Local, free, and a compliance check the plan did not ask for.

**Quotas** — request counts, never tokens (free tiers do not return trustworthy token
accounting). `QUOTA_GEMINI_REQUESTS=200`, `QUOTA_GROQ_REQUESTS=200`, persisted to SQLite.
Exhaustion **degrades** to the next provider and is recorded in `degraded_from`; it never raises.

**3D data** — the scene needs only: 4 zones × 56 forward days of forecast + 80 % prediction
interval, event bands (date + category), a daily weather ribbon, and promo state. ≈224 instanced
boxes; 60 fps is not in doubt. The map variant additionally needs a **stylised Dubai coastline**,
hand-simplified from Natural Earth 10 m (public domain) — no OSM, no tile provider, no key, no
runtime network call. Zone positions are the four real lat/lons.

---

## Architecture

FastAPI service (`services/api`) exposes provider-abstracted inference, RAG and marketing models
to a Next 16 web shell (`apps/web`). Both provider chains follow one shape: a `Protocol`, N
concrete providers ordered free-first, and a **deterministic stub as the terminal fallback** — so
the entire test suite runs with no model and no network. Persistence is SQLite + sqlite-vec, one
file, no server. Every piece of external text enters through one untrusted-content boundary and
carries a `trust` tag for its whole life. **No agent has a side-effect tool**; that is asserted
over the whole registry by a test, so a tool added later with a side effect fails the build.

**Stack:** Python 3.13 · uv · FastAPI · pydantic v2 · sqlite-vec · rank-bm25 · numpy · pandas ·
scikit-learn · pypdf · python-docx · reportlab · Ollama · pytest · ruff — Next 16 · React 19 ·
Tailwind v4 · next-themes · @react-three/fiber + drei · motion · Playwright · npm.

**15 tabs, four groups** (grouping is what stops 15 links being soup):

| Group | Tabs |
|---|---|
| **Plan** | Season (3D) · Forecast · Plan · Segments |
| **Make** | Creatives · Brand · Compliance · Panel |
| **Prove** | Measure · Experiments · Report |
| **System** | Ask · Crew · Data · Security |

### File structure (Phase A)

| Path | Responsibility |
| --- | --- |
| `services/api/core/llm.py` | `LLMProvider` protocol, 5 providers, `LLMChain`, provenance |
| `services/api/core/quota.py` · `killswitch.py` · `rbac.py` · `db.py` | budgets, refuse-all latch, Viewer/Analyst/Admin, SQLite+vec |
| `services/api/data/registry.py` | the dataset registry — every set carries source, licence, retrieved-at, and a `label` ∈ {observed, simulated, curated, sample} |
| `services/api/routers/data.py` | `/data/freshness`, `/data/zones`, `/data/events` |
| `pipeline/weather.py` · `calendar.py` · `events.py` · `footfall.py` | the four ETLs, each with `--verify` |
| `data/brand/sidra.yaml` | the single source of truth for the fictional brand |
| `apps/web/styles/tokens.almanac.css` · `tokens.souk.css` · `tokens.studio.css` | **three** complete directions, one gets locked in A2 |
| `apps/web/app/design/page.tsx` | the live comparison page the owner chooses from |
| `apps/web/scripts/check-contrast.mjs` | contrast gate over **every** direction × both registers |
| `scripts/spike_embeddings.py` · `placeholder_scan.py` | the A9 decision, the pre-artefact gate |

---

## Phase A — Data, ETL, shell, deploy

### Task A1 · Scaffold and the green bar
**Files:** `pyproject.toml`, `Makefile`, `.gitignore`, `.env.example`, `README.md`, `tests/test_smoke.py`, `apps/web/package.json`.
- [ ] Rename `master` → `main`; pin `requires-python = ">=3.13,<3.14"`.
- [ ] Write the failing smoke test first; create `services/api/__init__.py`; watch it pass.
- [ ] Scaffold `apps/web` (Next 16, React 19, Tailwind v4, next-themes) and `make check` = ruff + pytest + typecheck.

**Verifiable check:** `make check` exits 0.

### Task A2 · Three design directions, built — owner selects ⏸
**Files:** `apps/web/styles/tokens.{almanac,souk,studio}.css`, `apps/web/app/design/page.tsx`, `apps/web/scripts/check-contrast.mjs`, `docs/results/A2-contrast.json`.
- [ ] Author **all three** directions as complete OKLCH token sets, dark + light: **Almanac**
      (midnight indigo / bone paper, meteorological chart language, one warm heat ramp),
      **Night Souk** (indigo + brass, girih lattice structure), **Studio Editorial** (near-black /
      paper, oversized variable grotesk, bento).
- [ ] Build `/design`: the *same* real components — a forecast rail, a zone card, a creative
      card, a compliance badge, a data table — rendered live in each direction, both registers,
      at 360 px and 1440 px, with a one-click switcher.
- [ ] Contrast gate parses every direction × both registers: text ≥ 4.5:1, UI/borders ≥ 3:1.
      Raise values until **measured**, never estimated. Write every ratio to `docs/results/`.
- [ ] Load `premium-frontend` + `ui-ux-pro-max` before authoring; each direction must state its
      **one chroma rule** (what colour is allowed to mean) in a comment header.

**Verifiable check:** `node apps/web/scripts/check-contrast.mjs` exits 0 with a measured ratio for
every token pair in all 3 directions × 2 registers, and `/design` renders all three.
**⏸ STOP — owner picks one. The other two are deleted, not left as dead CSS.**

### Task A3 · The SIDRA brand kit
**Files:** `data/brand/sidra.yaml`, `scripts/build_brand_pdf.py`, `docs/brand/SIDRA-brand-guidelines.pdf`, `tests/brand/test_brand_kit.py`.
- [ ] `sidra.yaml`: identity, the 4 zones, tone-of-voice rules, palette, type, and every
      claim-to-avoid **mapped to a rule id and a source citation**.
- [ ] Generate the guideline PDF from that YAML (reportlab) — so the PDF can never drift from
      the rules the Compliance agent enforces. Page 1 states the brand is fictional.
- [ ] The PDF is also the first document in the RAG corpus.

**Verifiable check:** `uv run pytest tests/brand/` — every `claims_to_avoid` entry has a non-empty
`rule_id` and `source_url`; the PDF regenerates byte-identically from the YAML.

### Task A4 · Weather ETL
**Files:** `pipeline/weather.py`, `tests/data/test_weather.py`.
- [ ] Open-Meteo **archive**: 24 months hourly × 4 zone lat/lons — temp, apparent temp, humidity,
      precipitation, wind. Plus the 16-day forecast. Cache raw responses to `data/raw/`.
- [ ] Load to SQLite `weather_hourly`; label `observed`; record licence (CC BY 4.0, no key).

**Verifiable check:** `uv run python -m pipeline.weather --verify` → ≥ 17 000 rows per zone, no
gap > 3 h, writes `docs/results/A4-weather-etl.json`.

### Task A5 · Holidays and school calendar
**Files:** `pipeline/calendar.py`, `data/raw/uae_holidays.csv`, `data/raw/khda_terms.csv`.
- [ ] UAE public holidays, 24 months back + 12 forward. Nager.Date returned **204** for AE, so:
      derive Islamic dates with `hijri-converter`, cross-check every one against the u.ae
      announcement, and record the discrepancy policy in `docs/datasets.md`.
- [ ] KHDA term and break dates → CSV. Ramadan window flagged separately from Eid.

**Verifiable check:** `uv run pytest tests/data/test_calendar.py` — Eid al-Fitr 2025 and 2026
match the officially announced dates; no term overlaps a public holiday incorrectly.

### Task A6 · Events — curated, and labelled curated
**Files:** `pipeline/events.py`, `data/raw/dubai_events_24mo.csv`, `tests/data/test_events.py`.
- [ ] Visit Dubai returns **403** to non-browser clients, so build the curated CSV: **≥ 150
      events over 24 months** from public listings, each with title, start, end, venue, lat/lon,
      category, expected scale, `source_url`, `licence`, and `curated=true`.
- [ ] Enrich anchor events (DSF, DSS, GITEX, Ramadan, Eid, New Year) from the Wikipedia REST API
      (CC BY-SA 4.0, attributed).
- [ ] Compute `distance_km` from each event to each of the 4 zones — that is the feature the
      forecaster actually uses.

**Verifiable check:** `uv run python -m pipeline.events --verify` → ≥ 150 rows, every row complete
and `curated=true`, every `distance_km` present for all 4 zones; writes `docs/results/A6-events.json`.

### Task A7 · Footfall simulator and POS sample
**Files:** `pipeline/footfall.py`, `data/pos_sample.csv`, `tests/data/test_footfall.py`.
- [ ] Seeded hourly per-zone series, 24 months. **Bimodal dayparts** (morning and evening peaks,
      different per zone), weekly rhythm, mild trend, Ramadan re-shaping (daytime collapse,
      post-iftar surge), event coupling by `distance_km`, and **temperature elasticity that
      differs by zone** — Marina's outdoor seating steep, Mall of the Emirates flat.
- [ ] `simulated=true` on every row, in every API response, and on every chart that shows it.
- [ ] `data/pos_sample.csv` — basket-level sample for RFM, labelled `sample`.

**Verifiable check:** `uv run pytest tests/data/test_footfall.py` — byte-identical output for a
fixed seed; `DXB-MAR`'s fitted temperature coefficient is steeper than `DXB-MOE`'s by a stated
margin; a record constructed without `simulated=True` raises.

### Task A8 · Dataset registry and the freshness page
**Files:** `services/api/data/registry.py`, `services/api/routers/data.py`, `tests/api/test_freshness.py`.
- [ ] One registry entry per dataset: rows, span, source URL, licence, retrieved-at, and a
      `label` ∈ {observed, simulated, curated, sample}. A dataset **cannot be constructed without
      a licence and a label**.
- [ ] `/data/freshness` returns all of it; the Data tab renders it.

**Verifiable check:** `uv run pytest tests/api/test_freshness.py` — every dataset appears with a
non-null licence and label; adding one without either fails the suite.

### Task A9 · Embedding spike and `docs/models.md`
**Files:** `scripts/spike_embeddings.py`, `docs/models.md`, `docs/datasets.md`, `docs/results/A9-embedding-spike.json`.
- [ ] Probe EN/HI/AR translations of one SIDRA-domain claim plus an **unrelated control**. What
      counts is the **margin over the control**, not the raw similarity. Bar: ≥ 0.25 on both
      cross-lingual pairs. Candidates: `bge-m3:567m`, `nomic-embed-text`, and the deployable
      cloud/ONNX option.
- [ ] Write `docs/models.md` — no number typed by hand, every one from the results JSON.
      Record the GBR-over-Prophet decision and the `qwen3:4b` vs `qwen3:8b` split here too.
- [ ] Write `docs/datasets.md` from the verification table above, including the three sources
      that failed and the fallback used for each.

**Verifiable check:** `uv run python scripts/spike_embeddings.py` exits 0, the chosen model clears
0.25 on both pairs, and a disqualified model is *asserted* to stay disqualified.

### Task A10 · The web shell — 15 tabs, responsive, RTL, themed
**Files:** `apps/web/app/**`, `apps/web/components/{Masthead,Nav,ThemeToggle,LangToggle}.tsx`, `apps/web/e2e/shell.spec.ts`.
- [ ] All 15 routes in their 4 groups; the winning direction from A2 applied.
- [ ] Theme toggle (dark/light/system, persisted). EN/HI/AR with correct `dir=rtl` mirroring.
- [ ] Responsive 360 → 1920. Data tab renders live freshness from A8.

**Verifiable check:** `npx playwright test e2e/shell.spec.ts` — all 15 routes 200; theme choice
survives reload; **no horizontal scroll at 360 px**; axe reports 0 serious violations; RTL
mirrors the nav.

### Task A11 · Placeholder scan, README, CI
**Files:** `scripts/placeholder_scan.py`, `README.md`, `.github/workflows/check.yml`.
- [ ] Scan fails on TBD/TODO/lorem/XXX/`<placeholder>` anywhere in `docs/` or `README.md`.
- [ ] README states plainly, above the fold, that **SIDRA is a fictional brand built for this
      demo**, and that footfall is **simulated**.

**Verifiable check:** `uv run python scripts/placeholder_scan.py` exits 0 and `make check` is
green in CI.

### Task A12 · Deploy ⏸
**Files:** `render.yaml`, `apps/web/playwright.live.config.ts`, `docs/results/A12-deploy.json`.
- [ ] Render free web service (region `singapore`), ephemeral SQLite in `/tmp`, secrets set in
      the dashboard and never committed. Vercel for the web app. CORS pinned to the Vercel origin.
- [ ] README **Live** section with both URLs and an honest note that the free instance sleeps
      after 15 minutes so the first request takes ~50 s.

**Verifiable check:** `npx playwright test --config=playwright.live.config.ts` green against both
live URLs; writes `docs/results/A12-deploy.json`.
**⏸ STOP — needs your GitHub / Render / Vercel actions and your secrets.**

---

## Phases B–E (expanded at each phase boundary, not now)

- **B · Marketing models + notebook.** GBR forecast with exogenous drivers vs seasonal-naive
  (**target: beats naive on ≥ 70 % of weeks**); synthetic control + CUPED uplift
  (**injected +20 % recovered within ±5 pts**); RFM segmentation stable under bootstrap;
  channel × daypart allocator (sums to budget, monotone in ROI, equal marginal returns at the
  interior optimum). Every result to `docs/results/B*.json`.
- **C · API + LLMProvider + RAG + crew.** The five-provider chain with Anthropic hard-off;
  trilingual cited RAG over the SIDRA PDF, Codex CAC/GL 23-1997, MoEC and Dubai Municipality
  guidance; seven agents — Forecaster, Planner, Creative, Compliance, Panel, Measurer, Auditor —
  **none with a side-effect tool**, asserted over the registry. Compliance recall ≥ 0.9 on a
  40-case gold set. Creatives render as deterministic brand-accurate compositions in EN/AR/HI at
  three sizes; the free image tier is cached to disk so a live demo never waits on it;
  `qwen2.5vl:7b` reads the rendered creative back and re-runs the claim rules.
- **D · Web.** Season tab with **both** 3D variants — Demand Terrain (4 zone lanes × 56 days,
  event bands, weather ribbon, and a translucent cap on every block showing the 80 % prediction
  interval, so an uncertain forecast *looks* uncertain) and the Dubai Map extrusion — behind one
  toggle, `frameloop="demand"`, SVG fallback, reduced-motion respected. All 15 tabs live.
  Playwright journey: forecast → plan → creative → compliance → measure.
- **E · Harden and ship.** OWASP ASI scorecard + red-team harness, RBAC bound to identity, then
  `AI208_MAWSIM_report.docx`, deck, notebook, 15 viva questions, 3-minute demo — all generated
  **after** the placeholder scan is empty.

**After every phase:** deploy · update README **Live** and `docs/results/` · run the placeholder
scan · 5-line summary · stop and tell you what to click.

---

## Verification

```bash
make check          # ruff + pytest + contrast + placeholders + owasp + typecheck
make e2e            # Playwright, needs API + web running
uv run python -m pipeline.weather  --verify
uv run python -m pipeline.events   --verify
uv run python scripts/spike_embeddings.py
uv run python scripts/placeholder_scan.py
```

End-to-end, after Phase D: open the Season tab, scrub the 8-week terrain, toggle to the map,
click a high-demand Eid weekend in Marina, let the Planner propose a promo, generate creatives in
all three languages, watch Compliance fail one on a `sugar-free` claim with a Codex citation, fix
it, then open Measure and read the recovered lift with its confidence interval.

---

## Non-negotiables carried into every task

1. **Zero paid inference.** Ollama → Gemini free → Groq free → stub. Anthropic present and
   permanently off, enforced by a test, not by config.
2. **Only free, licensed data.** Every source in `docs/datasets.md` with URL, date, licence.
   An inaccessible source uses its named fallback and says so.
3. **Every number traces to `docs/results/`.** Every factual sentence in a generated report is
   cited. No agent has a side-effect tool. Nothing is ever published or executed externally —
   publishing is a human export.
4. **Tests green per task, one conventional commit per task** with the Claude co-author trailer.
   No per-task check-ins.
5. **Stop only** at phase ends, at secrets or Supabase/Render/Vercel/GitHub actions, at anything
   that costs money, at anything that moves a safety or "not advice" boundary — and at **A2**,
   where you pick the design direction.
