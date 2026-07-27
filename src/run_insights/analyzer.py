"""run data -> deterministic facts + flags, then LLM-drafted, grounded coaching feedback.

`analyze()` is pure math — NO LLM. It computes the split, pace fade, HR decoupling, effort type and
averages, and raises flags from them. `Coach` then asks the LLM for short feedback and a grounding
pass drops any numeric token in that feedback (a pace 'm:ss', an HR 'NNN bpm', a 'N%') that is not
one of the analyzer's computed facts — so the model can't invent a stat.

Illustrative demo — not coaching or medical advice.
"""

from __future__ import annotations

import re
from statistics import median

from . import prompts
from .client import LLMClient
from .models import Flag, RunData, RunInsights

# ── thresholds (documented, tunable) ─────────────────────────────────────────
NEG_SPLIT_STRONG = -2.0   # split % at/below which we call it a strong negative split
POS_SPLIT_FLAG = 2.0      # split % at/above which we flag a positive split
FADE_FLAG = 5.0           # pace fade % at/above which we flag fade
DECOUPLING_FLAG = 5.0     # decoupling % at/above which we flag aerobic decoupling
INTERVAL_CV = 8.0         # pace coefficient-of-variation % above which it looks like intervals
TEMPO_CV = 3.0            # CV % above which (but below interval) it looks like a tempo effort
LONG_KM = 16.0            # distance at/above which an easy-effort run is called 'long'


def _pace_to_seconds(pace: str) -> int:
    """'m:ss' -> total seconds. Raises ValueError on a malformed pace."""
    m = re.fullmatch(r"\s*(\d+):([0-5]\d)\s*", pace)
    if not m:
        raise ValueError(f"malformed pace {pace!r} (want 'm:ss')")
    return int(m.group(1)) * 60 + int(m.group(2))


def _seconds_to_pace(seconds: float) -> str:
    """total seconds -> 'm:ss' (rounded to the nearest second)."""
    total = int(round(seconds))
    return f"{total // 60}:{total % 60:02d}"


def _pct(new: float, base: float) -> float:
    return 0.0 if base == 0 else (new - base) / base * 100.0


def analyze(run: RunData) -> RunInsights:
    """Deterministic analysis of a single run. No LLM — pure arithmetic over the splits."""
    splits = run.splits
    if not splits:
        raise ValueError("run has no splits")

    paces = [_pace_to_seconds(s.pace) for s in splits]
    hrs = [s.hr for s in splits]
    n = len(splits)

    avg_pace_s = sum(paces) / n
    avg_hr = int(round(sum(hrs) / n))

    # ── split: 2nd-half avg pace vs 1st-half avg pace ────────────────────────
    half = n // 2
    if half >= 1 and n >= 2:
        first_half = paces[:half]
        second_half = paces[n - half:]  # symmetric halves; a middle km (odd n) is excluded from both
        split = round(_pct(sum(second_half) / len(second_half), sum(first_half) / len(first_half)), 1)
    else:
        split = 0.0

    # ── pace fade: last km vs first km ───────────────────────────────────────
    fade_pct = round(_pct(paces[-1], paces[0]), 1) if n >= 2 else 0.0

    # ── HR decoupling: 2nd-half HR:pace ratio vs 1st-half (cardiac drift) ─────
    # ratio = hr * pace_seconds (HR cost per unit of speed); rises as HR drifts or pace slows.
    if half >= 1 and n >= 2:
        r1 = [hrs[i] * paces[i] for i in range(half)]
        r2 = [hrs[i] * paces[i] for i in range(n - half, n)]
        decoupling_pct = round(_pct(sum(r2) / len(r2), sum(r1) / len(r1)), 1)
    else:
        decoupling_pct = 0.0

    # ── effort type: pace variability (CV) vs the run's own median + distance ─
    med = median(paces)
    if med > 0 and n >= 2:
        variance = sum((p - avg_pace_s) ** 2 for p in paces) / n
        cv = (variance**0.5) / med * 100.0
    else:
        cv = 0.0
    if cv >= INTERVAL_CV:
        effort_type = "interval"
    elif cv >= TEMPO_CV:
        effort_type = "tempo"
    elif run.distance_km >= LONG_KM:
        effort_type = "long"
    else:
        effort_type = "easy"

    flags: list[Flag] = []
    if split <= NEG_SPLIT_STRONG:
        flags.append(Flag(kind="strong_negative_split",
                          detail=f"Second half was {abs(split)}% faster than the first — a strong negative split."))
    elif split >= POS_SPLIT_FLAG:
        flags.append(Flag(kind="positive_split",
                          detail=f"Second half was {split}% slower than the first — a positive split."))
    if fade_pct >= FADE_FLAG:
        flags.append(Flag(kind="pace_fade",
                          detail=f"Last km was {fade_pct}% slower than the first km."))
    if decoupling_pct >= DECOUPLING_FLAG:
        flags.append(Flag(kind="hr_decoupling",
                          detail=f"Heart-rate to pace ratio drifted {decoupling_pct}% between halves "
                                 "(aerobic decoupling)."))

    return RunInsights(
        avg_pace=_seconds_to_pace(avg_pace_s),
        avg_hr=avg_hr,
        split=split,
        fade_pct=fade_pct,
        decoupling_pct=decoupling_pct,
        effort_type=effort_type,
        flags=flags,
        feedback="",
    )


# ── grounding filter ─────────────────────────────────────────────────────────
_PACE_RE = re.compile(r"\b\d{1,2}:[0-5]\d\b")
_HR_RE = re.compile(r"\b\d{2,3}\s?bpm\b", re.IGNORECASE)
_PCT_RE = re.compile(r"-?\d+(?:\.\d+)?\s?%")


def _computed_paces(insights: RunInsights) -> set[str]:
    return {insights.avg_pace}


def _computed_pcts(insights: RunInsights) -> set[float]:
    vals = {insights.split, insights.fade_pct, insights.decoupling_pct}
    # feedback may drop the sign or present the magnitude of a negative split, so allow abs too.
    return {round(abs(v), 1) for v in vals} | {round(v, 1) for v in vals}


def _pct_value(token: str) -> float:
    return round(float(token.replace("%", "").strip()), 1)


def _hr_value(token: str) -> int:
    return int(re.sub(r"\s?bpm", "", token, flags=re.IGNORECASE))


def ground_feedback(feedback: str, insights: RunInsights) -> str:
    """Drop the whole feedback if it contains a numeric claim (pace / bpm / %) that isn't a computed
    fact. A single fabricated stat poisons the message, so we fall back to a stat-free summary rather
    than surface a hallucinated number.
    """
    good_paces = _computed_paces(insights)
    good_pcts = _computed_pcts(insights)
    good_hr = insights.avg_hr

    for tok in _PACE_RE.findall(feedback):
        if tok not in good_paces:
            return _fallback(insights)
    for tok in _HR_RE.findall(feedback):
        if _hr_value(tok) != good_hr:
            return _fallback(insights)
    for tok in _PCT_RE.findall(feedback):
        if _pct_value(tok) not in good_pcts:
            return _fallback(insights)
    return feedback.strip()


def _fallback(insights: RunInsights) -> str:
    """A safe, stat-free summary used when the drafted feedback smuggled in a fabricated number."""
    if insights.flags:
        kinds = ", ".join(f.kind.replace("_", " ") for f in insights.flags)
        return f"This looks like a {insights.effort_type} effort. Worth a look: {kinds}."
    return f"This looks like a solidly-paced {insights.effort_type} effort — nothing notable to flag."


class Coach:
    """Composes the deterministic analysis with a grounded LLM feedback draft."""

    def __init__(self, client: LLMClient) -> None:
        self._client = client

    def insights(self, run: RunData) -> RunInsights:
        facts = analyze(run)
        draft = self._client.structured(
            schema=_Feedback,
            system=prompts.COACH_SYSTEM,
            user=prompts.coach_user(facts),
        )
        grounded = ground_feedback(draft.feedback, facts)
        return facts.model_copy(update={"feedback": grounded})


# Small internal schema for the LLM's single free-text field (keeps the tool call tidy).
from pydantic import BaseModel, Field  # noqa: E402


class _Feedback(BaseModel):
    feedback: str = Field(description="2–3 sentences of grounded coaching feedback.")
