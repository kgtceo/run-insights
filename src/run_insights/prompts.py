"""Coach prompt. Draft short feedback grounded ONLY in the numbers the analyzer already computed,
never invent a stat, and never give medical advice."""

from __future__ import annotations

from .models import RunInsights

COACH_SYSTEM = (
    "You write short, encouraging coaching feedback about a single run. You are given the objective "
    "numbers that a deterministic analyzer already computed from the run's splits. Use ONLY those "
    "numbers.\n\n"
    "Rules:\n"
    "1. Never invent or estimate a statistic. If you mention a pace, a heart rate, or a percentage, "
    "it MUST be one of the numbers provided. Prefer describing the pattern in words over quoting "
    "numbers.\n"
    "2. 2–3 sentences, plain and supportive. Explain what the split / fade / decoupling / effort "
    "type suggests about how the run went and one thing to try next time.\n"
    "3. Never give medical advice, diagnose anything, or comment on health/injury. This is about "
    "pacing and effort only.\n"
    "4. This is an illustrative demo, not coaching or medical advice."
)


def coach_user(facts: RunInsights) -> str:
    flags = "\n".join(f"- {f.kind}: {f.detail}" for f in facts.flags) or "- (none)"
    return (
        "Here are the computed facts for this run. Write the feedback using only these numbers.\n\n"
        f"average pace: {facts.avg_pace} /km\n"
        f"average HR: {facts.avg_hr} bpm\n"
        f"split: {facts.split}% (negative = 2nd half faster)\n"
        f"pace fade (last vs first km): {facts.fade_pct}%\n"
        f"HR decoupling: {facts.decoupling_pct}%\n"
        f"effort type: {facts.effort_type}\n"
        f"flags:\n{flags}"
    )
