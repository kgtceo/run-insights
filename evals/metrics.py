"""Deterministic eval metrics for run-insights.

  • recall     — the analyzer flags the planted pattern on a run that has it.
  • precision  — a clean, well-paced run is not over-flagged.
  • grounding  — every numeric token in the drafted feedback is a computed fact.
"""

from __future__ import annotations

import re

from run_insights.analyzer import _computed_pcts  # reuse the same "allowed %s" set
from run_insights.models import RunInsights

_PACE_RE = re.compile(r"\b\d{1,2}:[0-5]\d\b")
_HR_RE = re.compile(r"\b\d{2,3}\s?bpm\b", re.IGNORECASE)
_PCT_RE = re.compile(r"-?\d+(?:\.\d+)?\s?%")


def flag_kinds(result: RunInsights) -> set[str]:
    return {f.kind for f in result.flags}


def catches_pattern(result: RunInsights, planted_kinds: list[str]) -> bool:
    """Recall: the analyzer raised at least one of the planted flag kinds."""
    return bool(set(planted_kinds) & flag_kinds(result))


def not_overflagged(result: RunInsights, max_flags: int = 1) -> bool:
    """Precision: a clean run raises no more than `max_flags` flags (ideally 0)."""
    return len(result.flags) <= max_flags


def feedback_is_grounded(result: RunInsights) -> bool:
    """Every pace / HR / % token in the feedback is one of the analyzer's computed facts."""
    fb = result.feedback
    good_pcts = _computed_pcts(result)
    for tok in _PACE_RE.findall(fb):
        if tok != result.avg_pace:
            return False
    for tok in _HR_RE.findall(fb):
        if int(re.sub(r"\s?bpm", "", tok, flags=re.IGNORECASE)) != result.avg_hr:
            return False
    for tok in _PCT_RE.findall(fb):
        if round(float(tok.replace("%", "").strip()), 1) not in good_pcts:
            return False
    return True
