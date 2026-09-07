SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

.PHONY: check lint test web-check contrast palette redteam placeholders artefacts api web e2e smoke-live etl

UV := uv run

# The single green bar. Every task must leave this passing.
check: lint test contrast palette redteam placeholders web-check

# e2e is deliberately outside `check`: it needs the API and the web server
# running, so folding it in would make the default bar depend on two processes
# a contributor has not started.
e2e:
	cd apps/web && npx playwright test

# Alone and single-worker on purpose: see the note in playwright.config.ts.
frames:
	cd apps/web && npx playwright test --config=playwright.frames.config.ts

# Runs against the deployed pair. Set LIVE_API_URL and LIVE_WEB_URL first.
smoke-live:
	cd apps/web && npx playwright test --config=playwright.live.config.ts

lint:
	$(UV) ruff check services tests scripts pipeline
	$(UV) ruff format --check services tests scripts pipeline

test:
	$(UV) pytest -q

contrast:
	cd apps/web && node scripts/check-contrast.mjs

palette:
	cd apps/web && node scripts/check-palette.mjs

placeholders:
	$(UV) python scripts/placeholder_scan.py

# The red team runs inside `check`. A security claim is worth what the
# attempt to break it is worth, and an attempt nobody runs is worth nothing.
redteam:
	$(UV) python scripts/red_team.py

artefacts:
	$(UV) python scripts/build_report.py

web-check:
	cd apps/web && npm run typecheck

etl:
	$(UV) python -m pipeline.weather --verify
	$(UV) python -m pipeline.calendar --verify
	$(UV) python -m pipeline.events --verify
	$(UV) python -m pipeline.footfall --verify

api:
	$(UV) uvicorn services.api.main:app --reload --port 8000

web:
	cd apps/web && npm run dev
