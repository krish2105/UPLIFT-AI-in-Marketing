"""The UPLIFT / MAWSIM API.

Read-only by design. Every write in this application happens in a pipeline run
from a terminal, never from a request — there is no endpoint that mutates data,
and there is nothing here that reaches the outside world. Publishing a campaign
is a human action taken elsewhere.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.api import APP, BRAND_DISCLAIMER, COURSE
from services.api.routers import creative, data, health, marketing, series, system

app = FastAPI(
    title=f"{APP} — demand-aware promo planning",
    version="0.1.0",
    description=(
        f"{COURSE} coursework API. **{BRAND_DISCLAIMER}**\n\n"
        "Read-only: no endpoint mutates data and nothing here publishes or "
        "executes anything externally."
    ),
)

origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],  # the API is read-only; nothing else is permitted
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(data.router)
app.include_router(series.router)
app.include_router(marketing.router)
app.include_router(creative.router)
app.include_router(creative.compliance_router)
app.include_router(system.router)


@app.get("/", include_in_schema=False)
def root() -> dict:
    return {"app": APP, "docs": "/docs", "health": "/healthz", "disclaimer": BRAND_DISCLAIMER}
