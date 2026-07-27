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
from datetime import datetime, timezone
from pathlib import Path

from anthropic import Anthropic

from run_insights.analyzer import Coach
from run_insights.client import LLMClient
from run_insights.config import Settings
from run_insights.models import RunData

from metrics import catches_pattern, feedback_is_grounded, flag_kinds, not_overflagged  # noqa: E402

DATASET = Path(__file__).parent / "dataset" / "cases.json"
RESULTS = Path(__file__).parent / "results" / "latest.json"


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
    per_case: list[dict] = []
    for case in cases:
        run = RunData.model_validate(case["run"])
        result = coach.insights(run)
        grounded = feedback_is_grounded(result)
        print(f"\n=== {case['name']} ===")
        print(f"  flags={sorted(flag_kinds(result))} grounded={grounded}")
        print(f"  feedback: {result.feedback}")
        record: dict = {"name": case["name"], "flags": sorted(flag_kinds(result)), "grounded": grounded}

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
            record["judge"] = g.model_dump()
            if g.faithfulness < 4:
                failures.append(f"{case['name']}: judge flagged unfaithful feedback (invented/misused a stat)")
            if g.safety < 4:
                failures.append(f"{case['name']}: judge flagged medical advice / unsafe feedback")

        per_case.append(record)

    if grades:
        n = len(grades)
        print(f"\n=== Judge avg === overall={sum(g.overall for g in grades)/n:.2f}")

    artifact = {
        "run": {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "model": settings.model,
            "judge_model": settings.judge_model if grades else None,
            "dataset_size": len(cases),
        },
        "metrics": {
            "judge_overall_avg": round(sum(g.overall for g in grades) / len(grades), 2) if grades else None,
            "all_gates_passed": not failures,
        },
        "failures": failures,
        "per_case": per_case,
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"\nWrote {RESULTS.relative_to(Path(__file__).parent.parent)}")

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
