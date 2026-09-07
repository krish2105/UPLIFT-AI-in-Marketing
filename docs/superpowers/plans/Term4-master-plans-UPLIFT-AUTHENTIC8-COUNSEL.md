# Term 4 — Master Plans: UPLIFT (AI 208) · AUTHENTIC8 (AI 219) · COUNSEL (MGT 204)

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:writing-plans (expand each into a task-level plan with interfaces and tests, like RAQIB's), then superpowers:executing-plans, inline, no subagents. Checkbox syntax; every task green; conventional commits with the Claude co-author trailer.
>
> All three are **standalone repos** under `~/Desktop/MAIB-Term4/`, owner Krishna Mathur, solo. Patterns may be *read* from RAQIB and YIELDMAP (Control-Room tokens, `LLMProvider`, crew runtime, memory guard, OWASP harness, Term 4 doc builders) and **reimplemented, never imported**.
>
> **Shared decisions:** zero paid inference (`LLMProvider`: Ollama → Gemini free → Groq free; Anthropic present, off); Claude Code picks the embedding model after a spike (`docs/models.md`); EN/HI/AR with RTL; theme toggle; fully responsive; a 3D centrepiece per app (R3F, `frameloop="demand"`, SVG fallback); OWASP ASI scorecard and red-team harness in every repo; RBAC (Viewer/Analyst/Admin); every number traceable to `docs/results/`; placeholder scan empty before any Term 4 artefact is generated.
>
> **Build order:** YIELDMAP → COUNSEL → UPLIFT → AUTHENTIC8 (COUNSEL second because it reuses YIELDMAP's crew runtime patterns immediately and covers all four subjects in the presentation).

---

# 1. UPLIFT — AI in Marketing (AI 208)
### Demand-aware promo planner: events + weather + holidays + footfall → forecast → agent-planned campaigns → measured lift

Repo: `krish2105/UPLIFT-AI-in-Marketing`

## 1.1 Problem
Dubai retail demand swings with events, weather, holidays and school calendars, yet promotions are planned on gut feel. UPLIFT forecasts demand per store zone, lets a crew plan promotions and creatives against that forecast, checks brand and legal compliance, and then **measures incremental lift** rather than clicks — which is where 2026 marketing is heading: agentic execution, hyper-personalisation, and first-party data.

## 1.2 Data (all free)
- **Events:** Dubai Calendar / Visit Dubai public listings (title, dates, venue, category). Claude Code records URL, date and terms in `docs/datasets.md`; if a feed is not machine-readable, a curated CSV of ≥ 150 events for the last 24 months is built by hand from public listings and labelled as such.
- **Weather:** Open-Meteo historical + forecast API (free, no key).
- **Holidays:** UAE public holidays + KHDA school calendar (public), stored as CSV.
- **Footfall/demand proxy:** RAQIB's seeded footfall and checkout-served series (labelled `simulated=true`), plus a sample POS CSV labelled sample. A real POS export replaces it in any pilot.
- **Creatives corpus:** the brand's own past creatives and a public brand-guideline PDF (uploaded by the user).

## 1.3 Marketing layer (the AI 208 substance)
| Concept | Implementation | Test |
|---|---|---|
| Demand forecasting with exogenous drivers | GBR/Prophet on hourly footfall with event, weather, holiday, weekday features; MAE vs seasonal naive | beats naive on holdout |
| Uplift / incrementality | synthetic control per promo window (comparable non-promo days/zones), CUPED variance reduction; report lift with CI | injected +20% lift is recovered ±5 pts |
| Segmentation | RFM on POS sample; segment-level response curves | segments are stable under bootstrap |
| Media/channel mix | simple budget allocator (convex response curves) with what-if sliders | allocation sums to budget; monotone in ROI |
| Creative testing | crew generates variants; a persona panel (RAG-grounded in public reviews) scores them; scores feed the planner | panel is deterministic under seed |
| Brand & legal compliance | rules + RAG over brand guidelines and UAE advertising standards; every creative gets a pass/fail with citations | a non-compliant claim is caught |

## 1.4 RAG + Ask
Corpus: brand guidelines, UAE advertising/consumer-protection guidance (public), past campaign post-mortems (generated), event listings. Ask: "What lifted footfall most last Ramadan?", "Which weekends in Q4 have events within 2 km?", "Is this creative compliant?" — cited, trilingual.

## 1.5 Crew
| Agent | Tools | Output |
|---|---|---|
| Forecaster | `query_sql`, `forecast` | 8-week demand forecast with drivers |
| Planner | `forecast_lookup`, `allocate_budget` | promo calendar with expected lift and budget split |
| Creative | `ask` (RAG), `generate_variants` (text; images via free tier only if available) | 3 variants per slot, per language |
| Compliance | `ask`, `check_rules` | pass/fail with citations |
| Panel | `simulate_personas` | scores + confidence |
| Measurer | `query_sql`, `uplift` | post-campaign lift with CI |
| Auditor | `flag_run` | policy checks: uncited claims, budget breaches, non-compliant creatives that slipped |
No agent posts anything anywhere. Publishing is a human export.

## 1.6 Tabs
Calendar (3D: a **city-block timeline** — Dubai zones extruded by forecast demand, sweeping through the next 8 weeks with event and weather bands) · Forecast · Plan (calendar builder, budget sliders) · Creatives (variants, panel scores, compliance badges) · Measure (uplift charts with CI, synthetic control overlay) · Segments · Ask · Crew · Data · Security · Report.

## 1.7 Phases (≈ 6 weeks)
A Data & ETL (events, weather, holidays, footfall/POS; freshness page) → B Marketing models (forecast, uplift, RFM, allocator) + notebook → C API + `LLMProvider` + RAG + crew → D Web (3D timeline, all tabs, Playwright: forecast → plan → creative → compliance → measure) → E OWASP harness, deploy, Term 4 artefacts (`AI208_UPLIFT_report.docx`, deck, notebook, viva 15, demo 3 min).

## 1.8 Targets & limitations
Forecast beats naive on ≥ 70% of weeks; uplift recovery within ±5 pts on injected tests; compliance recall ≥ 0.9 on a 40-case set; 60 fps 3D. Limitations: footfall is RAQIB-simulated until a real POS/footfall export exists; persona panels complement, never replace, real customer research; image generation depends on free-tier availability.

---

# 2. AUTHENTIC8 — Ethics, Sociology & Governance of AI (AI 219)
### Synthetic-media provenance & deepfake triage: content credentials + detection ensemble + cited provenance reports

Repo: `krish2105/AUTHENTIC8-AI-in-Governance`

## 2.1 Problem
Synthetic images, voice and video are now cheap; institutions (newsrooms, HR, courts, banks doing video-KYC) need to say *how confident* they are that a media item is authentic and *why*. AUTHENTIC8 is a defensive triage tool: it verifies content credentials where present, runs an ensemble of open detectors, explains disagreement, and produces a provenance report with citations to the standards and to the evidence — while being honest that detection is probabilistic and can be fooled.

**Defensive only.** AUTHENTIC8 never generates deepfakes, never provides evasion guidance, and stores no biometric templates. Uploaded media is processed locally and deleted per the retention policy.

## 2.2 Data & models (all free/open, licences recorded)
- Content credentials: C2PA verification via the open `c2pa` Python bindings; test assets from the C2PA public samples.
- Image detection: 2–3 open-weight detectors from Hugging Face (Claude Code selects current, permissively licensed ones and records them in `docs/models.md`); classic forensics (ELA, noise residual, frequency artefacts) as a third, model-free signal.
- Audio detection: an open anti-spoofing model trained on ASVspoof-style data (licence checked); MFCC/spectral heuristics as fallback.
- Video: frame sampling → image ensemble + temporal consistency checks (blink/head-pose statistics), explicitly labelled as weak.
- Evaluation sets: publicly downloadable deepfake/real pairs whose licences allow research use (recorded); if a set requires a request form, the script exits with the instructions rather than downloading.

## 2.3 Governance layer (the AI 219 substance)
| Concept | Implementation |
|---|---|
| Provenance standards | C2PA manifest parse and signature check; report cites the manifest fields |
| Uncertainty & calibration | ensemble with reliability diagrams; calibrated probability, never a bare "fake"/"real" |
| Disagreement transparency | when detectors disagree, the report shows each signal and why |
| Harms & sociology | each report includes a harm-context section (political, financial, personal) drawn by RAG from public guidance (EU AI Act Article 50 transparency duties, UAE guidance, platform policies) with citations |
| Bias audit of the detector | per-skin-tone / per-language false-positive analysis on the eval set, published in the report |
| Human oversight | every conclusion is "advisory"; a reviewer must sign off before export; reviewer notes are stored |

## 2.4 RAG + Ask
Corpus: C2PA spec pages, EU AI Act Article 50 and recitals on synthetic content, UAE media/AI guidance, platform synthetic-media policies, academic surveys on detector limits. Ask: "What must a company label under Article 50?", "Why do the two image detectors disagree here?", "What is the false-positive rate for this detector on darker skin tones?" — cited.

## 2.5 Crew
Intake (hash, metadata, C2PA) → ImageAnalyst / AudioAnalyst / VideoAnalyst (run signals, no tools beyond model calls) → Calibrator (fuse, calibrate) → Narrator (RAG-cited report; zero side effects) → Auditor (flags uncited claims, over-confident language, missing bias section). Kill switch, budgets, guarded memory as elsewhere.

## 2.6 Tabs
Inbox (drag-drop media, queue) · Case (3D: a **provenance timeline** — the media item's manifest chain and every signal as nodes along a time axis, disagreement shown as spread) · Signals (per-detector heatmaps, spectrograms) · Calibration (reliability diagrams, thresholds) · Bias (subgroup FPR/FNR) · Ask · Crew · Security · Report.

## 2.7 Phases (≈ 6 weeks)
A Intake, hashing, C2PA verify, retention job → B Detectors + forensics + eval harness + calibration + bias audit + notebook → C API + `LLMProvider` + RAG + crew → D Web (3D timeline, all tabs, Playwright: upload → signals → report → reviewer sign-off → export) → E OWASP harness (plus: model-poisoning test on the detector weights hash; adversarial-sample robustness reported), deploy, Term 4 artefacts (`AI219_AUTHENTIC8_report.docx`, deck, notebook, viva 15, demo).

## 2.8 Targets & limitations
Ensemble AUC on the public eval set reported honestly with CI; ECE ≤ 0.05 after calibration; every report has a bias section and a reviewer signature; 100% citation coverage. Limitations: detectors degrade badly on unseen generators; video signals are weak; C2PA is absent on most real-world media today; AUTHENTIC8 is a triage aid, not evidence.

---

# 3. COUNSEL — Design Thinking (MGT 204)
### The AI boardroom: five agents argue a real decision with live data, output a decision memo, a dissent log and an outcome ledger

Repo: `krish2105/COUNSEL-Design-Thinking`

## 3.1 Problem
Design thinking asks teams to diverge before they converge — but solo founders and students have no room of experts to argue with. COUNSEL gives them one: agents with distinct mandates (CFO, CMO, COO, Ethics Officer, Devil's Advocate) research a decision with live public data, debate for N rounds, and converge on a memo that records what was decided, who dissented and why, and what evidence would change the view. Months later the user logs what actually happened, and the boardroom re-reads its own calibration.

## 3.2 Data (free)
Live web via a free search backend (SearXNG self-hosted in Docker, or a free-tier search API if Claude Code finds one; fallback: user-supplied links), Open-Meteo, DLD/YIELDMAP and RAQIB exports as optional "house data", and the user's own uploaded documents (business plan, interviews).

## 3.3 Design-thinking layer (the MGT 204 substance)
| Stage | COUNSEL feature |
|---|---|
| Empathise | Interview-transcript upload → cited persona cards and an empathy map |
| Define | Problem-framing round: agents propose HMW statements; user picks |
| Ideate | Divergence round with a "no critique" rule enforced by the Auditor; idea board |
| Prototype | Each idea gets a one-page prototype spec and a mock screen (SVG) |
| Test | Debate rounds on the top 3 with desirability/feasibility/viability scoring; dissent log |
| Decide | Decision memo (Amazon-style 1-pager), pre-mortem, "what would change our mind" |
| Learn | Outcome ledger: user records results; Brier-score calibration per agent over time |

## 3.4 RAG + Ask
Corpus: uploaded documents, debate transcripts, decision memos, outcome ledger. Ask: "Why did the CFO dissent on option B?", "What did the Ethics Officer flag last time we discussed pricing?", "Which of our past decisions were over-confident?" — cited to transcript spans.

## 3.5 Crew and rules
Five debating agents + Facilitator (turn-taking, round limits, enforces stage rules) + Auditor (flags ad-hominem, unsupported numbers, stage-rule breaches). Each debating agent has `search` and `ask` only; the Facilitator has `start_round`, `close_round`; nobody has side-effect tools. Budgets per session; kill switch. Transcripts are signed per message so the replay is tamper-evident.

## 3.6 Tabs
Room (3D: a **round table** — five agent avatars as abstract forms whose glow follows speaking turns; argument edges arc between them; replay slider) · Stages (Empathise → Learn stepper) · Board (idea cards, votes) · Memo (decision 1-pager, dissent log, pre-mortem, export) · Ledger (outcomes, calibration chart per agent) · Ask · Crew · Security · Report.

## 3.7 Phases (≈ 5 weeks)
A Scaffold, `LLMProvider`, search backend, document upload + RAG → B Crew: facilitator, five mandates as prompt files with explicit values and blind spots, auditor, signed transcripts → C Stages engine, scoring, memo/pre-mortem generation, outcome ledger + Brier scoring → D Web (3D round table with replay, all tabs, Playwright: upload → define → debate 3 rounds → memo → log outcome) → E OWASP harness (goal hijack via a poisoned uploaded document must not change the memo; agent impersonation via unsigned message rejected), deploy, Term 4 artefacts (`MGT204_COUNSEL_report.docx`, deck, viva 15, demo). The demo decision: "Should RAQIB pilot in a Dubai hypermarket or a Greenlam plant first?" — real, and it ties your projects together on stage.

## 3.8 Targets & limitations
A full 3-round debate on a 7B local model in < 4 minutes; every memo claim cited to a transcript span or source; Auditor catches ≥ 90% of seeded stage-rule breaches; 60 fps 3D. Limitations: agents' "expertise" is prompt-defined; calibration needs many logged outcomes to mean anything; search quality depends on the free backend.

---

## Viva themes shared across the three
Why bounded, side-effect-free agents; how citations are enforced; what the Auditor checks; where the 3D view could mislead and how normalisation prevents it; what free-tier constraints forced you to design better; what each project would need to become a product.

## First instruction to Claude Code (each repo)
"Read this master plan section for <PROJECT>. Create the repo and workspace. Run `ollama list`. Verify each data source listed (fetch a sample; record URL, date, licence in `docs/datasets.md`; report anything not accessible and the fallback you will use). List assumptions about models, quotas and 3D data. Expand Phase A into a task-level plan with interfaces and one verifiable check per task. Wait for my 'go'."
