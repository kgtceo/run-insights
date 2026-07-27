"""Run the run-insights eval suite.

Gates:
  • RECALL     — on a run with a planted pattern, the analyzer raises the planted flag(s).
  • PRECISION  — on a clean, well-paced run, the analyzer does not over-flag.
  • GROUNDING  — every pace / HR / % in the drafted feedback is a computed fact (no invented stat).
  • JUDGE      — (optional, --judge) opus scores faithfulness / usefulness / safety of the feedback.

    python evals/run_evals.py            # deterministic gates only (runs the LLM for feedback)
    python evals/run_evals.py --judge    # also run the opus judge
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from anthropic import Anthropic

from run_insights.analyzer import Coach
from run_insights.client import LLMClient
from run_insights.config import Settings
from run_insights.models import RunData

from metrics import catches_pattern, feedback_is_grounded, flag_kinds, not_overflagged  # noqa: E402

DATASET = Path(__file__).parent / "dataset" / "cases.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", action="store_true", help="Also run the opus faithfulness/safety judge.")
    args = ap.parse_args()

    settings = Settings.from_env()
    anthropic = Anthropic(api_key=settings.anthropic_api_key)
    client = LLMClient(settings, anthropic)
    coach = Coach(client)
    cases = json.loads(DATASET.read_text())

    failures: list[str] = []
    grades = []
    for case in cases:
        run = RunData.model_validate(case["run"])
        result = coach.insights(run)
        grounded = feedback_is_grounded(result)
        print(f"\n=== {case['name']} ===")
        print(f"  flags={sorted(flag_kinds(result))} grounded={grounded}")
        print(f"  feedback: {result.feedback}")

        if not grounded:
            failures.append(f"{case['name']}: feedback contains a stat that isn't a computed fact")
        if case["expect_flags"]:
            if not catches_pattern(result, case["planted_kinds"]):
                failures.append(f"{case['name']}: analyzer missed the planted pattern {case['planted_kinds']}")
        else:
            if not not_overflagged(result):
                failures.append(f"{case['name']}: over-flagged a clean, well-paced run (precision)")

        if args.judge:
            from judge import grade  # noqa: E402

            g = grade(result, settings, client)
            grades.append(g)
            print(f"  JUDGE: faithfulness={g.faithfulness} usefulness={g.usefulness} safety={g.safety} overall={g.overall}")
            if g.faithfulness < 4:
                failures.append(f"{case['name']}: judge flagged unfaithful feedback (invented/misused a stat)")
            if g.safety < 4:
                failures.append(f"{case['name']}: judge flagged medical advice / unsafe feedback")

    if grades:
        n = len(grades)
        print(f"\n=== Judge avg === overall={sum(g.overall for g in grades)/n:.2f}")

    print("\n" + "=" * 40)
    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  ✗ {f}")
        return 1
    print("ALL GATES PASSED ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
