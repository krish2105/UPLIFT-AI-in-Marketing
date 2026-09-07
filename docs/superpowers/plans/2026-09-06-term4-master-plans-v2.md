1. UPLIFT — AI in Marketing (AI 208)
Demand-aware promo planner: events + weather + holidays + footfall → forecast → agent-planned campaigns → measured lift

Repo: krish2105/UPLIFT-AI-in-Marketing

1.1 Problem
Dubai retail demand swings with events, weather, holidays and school calendars, yet promotions are planned on gut feel. UPLIFT forecasts demand per store zone, lets a crew plan promotions and creatives against that forecast, checks brand and legal compliance, and then measures incremental lift rather than clicks — which is where 2026 marketing is heading: agentic execution, hyper-personalisation, and first-party data.

1.2 Data (all free)
- Events: Dubai Calendar / Visit Dubai public listings (title, dates, venue, category). Claude Code records URL, date and terms in docs/datasets.md; if a feed is not machine-readable, a curated CSV of ≥ 150 events for the last 24 months is built by hand from public listings and labelled as such.
- Weather: Open-Meteo historical + forecast API (free, no key).
- Holidays: UAE public holidays + KHDA school calendar (public), stored as CSV.
- Footfall/demand proxy: RAQIB's seeded footfall and checkout-served series (labelled simulated=true), plus a sample POS CSV labelled sample. A real POS export replaces it in any pilot.
- Creatives corpus: the brand's own past creatives and a public brand-guideline PDF (uploaded by the user).

1.3 Marketing layer (the AI 208 substance)
Concept	Implementation	Test
Demand forecasting with exogenous drivers	GBR/Prophet on hourly footfall with event, weather, holiday, weekday features; MAE vs seasonal naive	beats naive on holdout
Uplift / incrementality	synthetic control per promo window (comparable non-promo days/zones), CUPED variance reduction; report lift with CI	injected +20% lift is recovered ±5 pts
Segmentation	RFM on POS sample; segment-level response curves	segments are stable under bootstrap
Media/channel mix	simple budget allocator (convex response curves) with what-if sliders	allocation sums to budget; monotone in ROI
Creative testing	crew generates variants; a persona panel (RAG-grounded in public reviews) scores them; scores feed the planner	panel is deterministic under seed
Brand & legal compliance	rules + RAG over brand guidelines and UAE advertising standards; every creative gets a pass/fail with citations	a non-compliant claim is caught

1.4 RAG + Ask
Corpus: brand guidelines, UAE advertising/consumer-protection guidance (public), past campaign post-mortems (generated), event listings. Ask: "What lifted footfall most last Ramadan?", "Which weekends in Q4 have events within 2 km?", "Is this creative compliant?" — cited, trilingual.

1.5 Crew
Agent	Tools	Output
Forecaster	query_sql, forecast	8-week demand forecast with drivers
Planner	forecast_lookup, allocate_budget	promo calendar with expected lift and budget split
Creative	ask (RAG), generate_variants (text; images via free tier only if available)	3 variants per slot, per language
Compliance	ask, check_rules	pass/fail with citations
Panel	simulate_personas	scores + confidence
Measurer	query_sql, uplift	post-campaign lift with CI
Auditor	flag_run	policy checks: uncited claims, budget breaches, non-compliant creatives that slipped
No agent posts anything anywhere. Publishing is a human export.		

1.6 Tabs
Calendar (3D: a city-block timeline — Dubai zones extruded by forecast demand, sweeping through the next 8 weeks with event and weather bands) · Forecast · Plan (calendar builder, budget sliders) · Creatives (variants, panel scores, compliance badges) · Measure (uplift charts with CI, synthetic control overlay) · Segments · Ask · Crew · Data · Security · Report.

1.7 Phases (≈ 6 weeks)
A Data & ETL (events, weather, holidays, footfall/POS; freshness page) → B Marketing models (forecast, uplift, RFM, allocator) + notebook → C API + LLMProvider + RAG + crew → D Web (3D timeline, all tabs, Playwright: forecast → plan → creative → compliance → measure) → E OWASP harness, deploy, Term 4 artefacts (AI208_MAWSIM_report.docx, deck, notebook, viva 15, demo 3 min).

1.8 Targets & limitations
Forecast beats naive on ≥ 70% of weeks; uplift recovery within ±5 pts on injected tests; compliance recall ≥ 0.9 on a 40-case set; 60 fps 3D. Limitations: footfall is RAQIB-simulated until a real POS/footfall export exists; persona panels complement, never replace, real customer research; image generation depends on free-tier availability.
⸻
