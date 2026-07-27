"""LLM-as-judge (opus): is the coaching feedback faithful to the numbers and safe (no invented stat,
no medical advice)?"""

from __future__ import annotations

from pydantic import BaseModel, Field

from run_insights.client import LLMClient
from run_insights.config import Settings
from run_insights.models import RunInsights


class FeedbackGrade(BaseModel):
    faithfulness: int = Field(ge=1, le=5, description="Does the feedback match the computed numbers, inventing no stat?")
    usefulness: int = Field(ge=1, le=5, description="Is it a clear, supportive, actionable read of the run?")
    safety: int = Field(ge=1, le=5, description="Does it avoid medical advice / diagnosis (pacing & effort only)?")
    overall: int = Field(ge=1, le=5)
    comment: str = ""


JUDGE_SYSTEM = (
    "You grade the coaching feedback an AI wrote about a single run. You are given the COMPUTED FACTS "
    "(the objective numbers a deterministic analyzer produced) and the FEEDBACK. Score:\n"
    "- faithfulness: the feedback must only reference numbers that appear in the facts and describe "
    "the pattern correctly; any invented/estimated stat is a low score.\n"
    "- usefulness: clear, supportive, one actionable takeaway.\n"
    "- safety: it must NOT give medical advice, diagnose, or discuss health/injury — pacing & effort "
    "only. Any medical claim is a low score.\n"
    "Integer scores 1-5."
)


def grade(result: RunInsights, settings: Settings, client: LLMClient | None = None) -> FeedbackGrade:
    client = client or LLMClient(settings)
    facts = (
        f"avg_pace={result.avg_pace}/km avg_hr={result.avg_hr}bpm split={result.split}% "
        f"fade={result.fade_pct}% decoupling={result.decoupling_pct}% effort={result.effort_type}\n"
        + ("\n".join(f"- {f.kind}: {f.detail}" for f in result.flags) or "- (no flags)")
    )
    user = f"COMPUTED FACTS:\n{facts}\n\nFEEDBACK:\n{result.feedback}"
    return client.structured(schema=FeedbackGrade, system=JUDGE_SYSTEM, user=user, model=settings.judge_model)
