# Redeploy runbook

Written for someone with **no memory of building this**, working from a
downloaded zip of the repository, months from now. That person may be me.

Every step is either a command to run or a field to fill in. Where a step needs
something this repository deliberately does not contain — a secret, a dashboard
setting — it says so and says where to get it.

**There is no Supabase and no Postgres.** The database is SQLite, one file,
rebuilt from the pipelines. If an instruction elsewhere mentions `pg_dump`, it
is not describing this project.

---

## 0 · What you are restoring

| Piece | Where it runs | Defined by |
|---|---|---|
| API (FastAPI, SQLite) | Render free web service, region `singapore` | `render.yaml` |
| Web app (Next 16) | Vercel | `vercel.json` + project root `apps/web` |
| Database | a file inside the API's own filesystem | `services/api/core/db.py` migrations |

Free tiers throughout. Nothing here costs money, and nothing needs a paid model.

---

## 1 · Prerequisites

```bash
# macOS; use the equivalent on Linux
brew install uv node git gh sqlite
```

- **Python 3.13** — `uv` installs it; `pyproject.toml` pins `>=3.13,<3.14`.
- **Node 20+** for the web app and the design gates.
- **Ollama** only if you want the local model tier. The application runs without
  it, on a deterministic stub, and `/healthz` says which.

```bash
git clone https://github.com/krish2105/UPLIFT-AI-in-Marketing.git
cd UPLIFT-AI-in-Marketing
uv sync --extra dev
cd apps/web && npm install && cd ../..
```

---

## 2 · Get a database — snapshot first, ingestion as the fallback

**Option A — restore the snapshot (about 30 seconds).** This is the fast path.

```bash
mkdir -p data/processed
gunzip -c data/snapshot/AI208_MAWSIM_20260908.sql.gz | sqlite3 data/processed/uplift.db
```

Verify: 72,192 weather rows, 72,192 footfall rows, 245 events, 8,737 baskets.

```bash
uv run python -c "import sqlite3;c=sqlite3.connect('data/processed/uplift.db');print({t:c.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ('weather_hourly','footfall_hourly','events','pos_baskets')})"
```

**Option B — re-run ingestion from scratch (20–40 minutes).** Use this if the
snapshot is missing, or if you want data more recent than the snapshot's date.

```bash
make etl
```

This works because **every source is free and reproducible**: Open-Meteo needs no
key, the UAE calendar is computed with `hijridate`, the events set is a curated
CSV committed to this repository, and the footfall series is generated from a
fixed seed — byte-identical every run, asserted by a test.

The weather ETL is the slow part; it fetches 24 months of hourly history for
four sites. It caches raw responses under `data/raw/`, so a second run is fast.

---

## 3 · Run it locally and confirm it works

```bash
make check     # ruff, 290+ pytest, contrast, palette, red team, placeholders, typecheck
make api       # http://localhost:8000/docs
make web       # http://localhost:3000
make e2e       # Playwright; starts both servers itself
make frames    # the 3D frame-budget measurement, run alone
```

**The one flow to check by hand** is the journey asserted by
`apps/web/e2e/journey.spec.ts::"a planner can go from a forecast to a measured
lift"`, which walks `/forecast` → `/plan` → `/creatives` → `/compliance` →
`/measure` in that order. Open the Compliance tab, type `Our best sugar-free detox latte`, and
confirm three findings appear with rule ids. Then type
`Was AED 32, now AED 24. Until 30 September.` and confirm it passes — the
false-positive case matters as much as the true-positive one.

---

## 4 · Local models (optional)

Only if you want the local tier rather than the stub. The exact tags this
project used, from `docs/models.md`:

```bash
ollama pull qwen3:8b            # reasoning-heavy roles
ollama pull qwen3:4b-instruct   # high-volume schema-constrained replies
ollama pull bge-m3:567m         # embeddings — chosen by the A9 spike
```

`nomic-embed-text` is **disqualified** and a test asserts it stays that way; do
not substitute it. `qwen2.5vl:7b` appears in `docs/models.md` as a planned
vision check that **was never built** — you do not need it.

Confirm the retrieval mode the instance is actually in:

```bash
curl -s localhost:8000/healthz | python3 -m json.tool | head -12
```

`retrieval: hybrid` means an embedder was found; `lexical` means none was, which
is a supported state and not a failure.

---

## 5 · Deploy the API to Render

1. Create a Render account and a **new Blueprint** pointed at this repository.
   `render.yaml` defines the service; do not create the service by hand.
2. Region must be **singapore** and plan **free** (both are in the blueprint).
3. Set the environment variables Render marks `sync: false`. Every name is in
   `.env.example`; **the values are not in this repository and never will be** —
   they come from your password manager.
   - `UPLIFT_SIGNING_SECRET` — optional. Unset, there is no Admin role at all,
     which is the correct default for a public URL. See `docs/deploy.md`.
   - `GEMINI_API_KEY`, `GROQ_API_KEY` — optional; without them the chain ends
     at the deterministic stub.
4. The build command runs the four pipelines, so the first deploy takes several
   minutes and needs no snapshot. **`UPLIFT_DB` must stay repo-relative** —
   Render's build and runtime are different containers, and a database written
   to `/tmp` is gone before the service starts.
5. Update `CORS_ORIGINS` in `render.yaml` to your new Vercel URLs and push.

---

## 6 · Deploy the web app to Vercel

1. Import this repository into Vercel.
2. **Set the project's Root Directory to `apps/web`.** This is the one setting
   that cannot live in `vercel.json`, and it is the most common way this
   deployment fails to reproduce.
3. `NEXT_PUBLIC_API_BASE` is optional: `next.config.ts` falls back to the
   production Render URL when `VERCEL` is set. If your API URL differs, set it.
4. Redeploy the API after step 5.5 so CORS matches, or the web app will render
   its honest "API unreachable" state on every tab.

---

## 7 · Verify the live pair

```bash
# The URLs this project was last verified against. Substitute your own if you
# created fresh services in steps 5 and 6.
export LIVE_API_URL=https://mawsim-api.onrender.com
export LIVE_WEB_URL=https://uplift-mawsim.vercel.app
uv run python scripts/verify_deploy.py   # 10 checks
make smoke-live                          # 7 browser checks
```

Three things to confirm by eye:

- **The live URL loads** and the Season tab renders the 3D terrain.
- **The core flow works**: Compliance rejects the sugar-free line with a rule id.
- **The Security tab is clean**: 10 of 10 OWASP ASI controls enforced, and the
  attack table shows 48 of 48 held with no unaccepted breaks.

**The free instance sleeps after 15 minutes.** The first request then takes about
fifty seconds. That is not an outage; open `/healthz` a minute before a demo.

---

## 8 · Regenerate the submission artefacts

```bash
uv run python scripts/build_report.py   # report .md + .docx, deck .pptx, viva, demo, notebook
```

Everything in `docs/artefacts/` is generated from `docs/results/`. Do not edit
those files by hand — `tests/test_artefacts_are_current.py` compares each one
against what its builder produces and fails if they differ.

**Open `AI208_MAWSIM_deck.pptx` once in PowerPoint before submitting.** It was
built without LibreOffice available, so it was checked arithmetically for
overflow and overlap (`tests/test_deck_geometry.py`) rather than looked at.

---

## 9 · Time estimates

| Path | Time |
|---|---|
| Clone, install, restore snapshot, `make check` green | **~10 minutes** |
| Clone, install, full re-ingestion, `make check` green | **~45 minutes** |
| Add both cloud deploys and verify live | **+30 minutes** |

---

## 10 · What this repository deliberately does not contain

Stated so you do not go looking:

- **No real secrets.** `.env.example` carries names only, asserted by
  `tests/test_env_example_matches_the_code.py`.
- **No Vercel project id or Render service id in code.** They are account-scoped;
  create fresh ones.
- **No committed `uplift.db`.** It is generated. The snapshot under
  `data/snapshot/` exists so you do not have to wait for ingestion.
- **No clause text from the Codex standards.** Their PDFs return 403 to scripted
  clients, so eight of eleven rules cite a section rather than a quotation and
  say so. This is recorded in `docs/datasets.md`, not hidden.
