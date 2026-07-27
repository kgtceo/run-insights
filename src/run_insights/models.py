"""Typed contracts for run-insights.

The analyzer reads a single run's per-km splits and returns objective, deterministic facts
(split, pace fade, HR decoupling, effort type, averages) plus flags. An LLM then drafts short
coaching feedback grounded in those numbers, and a grounding pass drops any numeric claim in the
feedback that isn't one of the computed facts — so it can't invent a stat. Illustrative demo —
not coaching or medical advice.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Split(BaseModel):
    km: int = Field(description="1-based kilometre index.")
    pace: str = Field(description="Pace for this km as 'm:ss' per km, e.g. '5:12'.")
    hr: int = Field(description="Average heart rate over this km, in bpm.")


class RunData(BaseModel):
    """A single run: its per-km splits, total distance and elevation."""

    splits: list[Split] = Field(description="Per-km splits, in order.")
    distance_km: float = Field(description="Total distance in km.")
    elevation_m: float = Field(description="Total elevation gain in metres.")


class Flag(BaseModel):
    kind: str = Field(
        description="Short label, e.g. 'positive_split', 'pace_fade', 'hr_decoupling', "
        "'strong_negative_split'.",
    )
    detail: str = Field(description="Plain-English detail, grounded in a computed number.")


class RunInsights(BaseModel):
    """The analysis of one run: deterministic facts, flags, and grounded coaching feedback."""

    avg_pace: str = Field(description="Average pace over the run as 'm:ss' per km.")
    avg_hr: int = Field(description="Average heart rate over the run, in bpm.")
    split: float = Field(
        description="Split percentage: negative if the 2nd half was faster (negative split), "
        "positive if slower (positive split). e.g. -3.2 means 2nd half 3.2% faster.",
    )
    fade_pct: float = Field(
        description="Pace fade: % slowdown of the last km vs the first km. Positive = slowed down.",
    )
    decoupling_pct: float = Field(
        description="Aerobic decoupling: % change in the 2nd-half HR:pace ratio vs the 1st half. "
        ">~5% suggests aerobic decoupling / cardiac drift.",
    )
    effort_type: str = Field(
        description="'easy' | 'tempo' | 'interval' | 'long' — inferred from pace variability and "
        "distance vs the run's own median pace.",
    )
    flags: list[Flag] = Field(default_factory=list)
    feedback: str = Field(default="", description="Short coaching feedback, grounded in the facts.")
    disclaimer: str = (
        "Illustrative demo — not coaching or medical advice. It summarises objective numbers from a "
        "single run; it does not know your training history, health, or goals. Synthetic data only."
    )
