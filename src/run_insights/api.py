"""FastAPI wrapper: submit a run's splits → deterministic facts + flags + grounded coaching feedback."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings
from .data.sample_runs import SAMPLE_RUNS
from .models import RunData, RunInsights

app = FastAPI(title="run-insights", version="1.0.0")

_env_origins = [o.strip() for o in os.getenv("RI_CORS_ORIGINS", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_env_origins,
    allow_origin_regex=r"https://run-insights[a-z0-9-]*\.vercel\.app|http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/samples")
def samples() -> dict:
    """The baked-in synthetic runs, keyed by name (for the 'Load example' buttons)."""
    return {name: run.model_dump() for name, run in SAMPLE_RUNS.items()}


@app.post("/api/insights")
def insights(run: RunData) -> RunInsights:
    if not run.splits:
        raise HTTPException(status_code=422, detail="run has no splits")
    try:
        settings = Settings.from_env()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    from .analyzer import Coach
    from .client import LLMClient

    try:
        return Coach(LLMClient(settings)).insights(run)
    except ValueError as exc:  # malformed pace etc.
        raise HTTPException(status_code=422, detail=str(exc)) from exc
