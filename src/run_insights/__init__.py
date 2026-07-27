"""run-insights — an AI running-activity analyzer.

Feed it a single run's per-km splits ({km, pace, hr}) plus distance and elevation. A deterministic
analyzer computes the objective facts — split (negative/positive), pace fade, HR decoupling, effort
type, averages — and raises flags. An LLM then drafts short coaching feedback grounded in exactly
those numbers, and a grounding filter drops any fabricated pace / bpm / % so it can't hallucinate a
stat. Ships a planted-pattern eval harness. Illustrative demo — not coaching or medical advice."""

from .analyzer import Coach, analyze, ground_feedback
from .client import LLMClient
from .config import Settings
from .models import Flag, RunData, RunInsights, Split

__all__ = [
    "LLMClient",
    "Settings",
    "Split",
    "RunData",
    "Flag",
    "RunInsights",
    "analyze",
    "ground_feedback",
    "Coach",
]
