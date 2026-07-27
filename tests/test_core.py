"""Core offline tests (fake client, no API key):

  • the deterministic analyzer's split / fade / decoupling / averages math on a known run
  • the grounding filter drops feedback that smuggles in a fabricated pace / HR / %
"""

from __future__ import annotations

import pytest
from conftest import FakeClient

from run_insights.analyzer import Coach, analyze, ground_feedback
from run_insights.models import RunData, Split


def _run(rows, distance_km=4.0, elevation_m=10.0):
    return RunData(
        splits=[Split(km=k, pace=p, hr=h) for k, p, h in rows],
        distance_km=distance_km,
        elevation_m=elevation_m,
    )


# A hand-computable run: 1st half 5:00 @140bpm, 2nd half 4:30 @150bpm.
KNOWN = _run([(1, "5:00", 140), (2, "5:00", 140), (3, "4:30", 150), (4, "4:30", 150)])


def test_analyzer_math_on_known_run():
    r = analyze(KNOWN)
    # avg pace = (300+300+270+270)/4 = 285s = 4:45 ; avg hr = 145
    assert r.avg_pace == "4:45"
    assert r.avg_hr == 145
    # split: 2nd half (270) vs 1st half (300) -> (270-300)/300 = -10.0% (negative = faster)
    assert r.split == -10.0
    # fade: last km (270) vs first km (300) -> -10.0%
    assert r.fade_pct == -10.0
    # decoupling: 2nd-half hr*pace (40500) vs 1st-half (42000) -> -3.6%
    assert r.decoupling_pct == -3.6
    # strong negative split gets flagged; nothing else on this clean run
    assert [f.kind for f in r.flags] == ["strong_negative_split"]


def test_positive_split_and_fade_and_decoupling_flags():
    # 1st half fast/low-HR, 2nd half slow/high-HR -> positive split, fade, and HR decoupling.
    run = _run([(1, "5:00", 145), (2, "5:00", 147), (3, "5:40", 162), (4, "5:50", 168)])
    r = analyze(run)
    assert r.split > 0            # 2nd half slower
    assert r.fade_pct > 0         # last km slower than first
    assert r.decoupling_pct > 5   # HR drifted up relative to pace
    kinds = {f.kind for f in r.flags}
    assert {"positive_split", "pace_fade", "hr_decoupling"} <= kinds


def test_grounding_filter_drops_fabricated_pace():
    r = analyze(KNOWN)  # avg_pace 4:45, avg_hr 145, split/fade -10.0, decoupling -3.6
    # A fabricated pace (3:59) that is NOT the computed avg pace must poison the message.
    bad = "Great job holding 3:59 pace throughout — really strong."
    grounded = ground_feedback(bad, r)
    assert "3:59" not in grounded  # fabricated stat dropped
    # falls back to a safe, stat-free summary
    assert grounded != bad
    assert "negative split" in grounded  # mentions the real flag, no numbers


def test_grounding_filter_keeps_real_numbers():
    r = analyze(KNOWN)
    good = f"Nice negative split. You averaged {r.avg_pace} at {r.avg_hr} bpm and closed {abs(r.split)}% quicker."
    assert ground_feedback(good, r) == good.strip()


def test_grounding_filter_drops_fabricated_hr_and_pct():
    r = analyze(KNOWN)
    assert ground_feedback("Your heart rate sat around 999 bpm.", r) != "Your heart rate sat around 999 bpm."
    assert "50%" not in ground_feedback("You slowed by 50% in the back half.", r)


def test_coach_composes_analysis_with_grounded_feedback():
    # Fake LLM returns a fabricated pace; Coach must strip it out but keep the real analysis.
    coach = Coach(FakeClient("You cruised at 2:11 pace the whole way."))
    result = coach.insights(KNOWN)
    assert result.avg_pace == "4:45"                 # real computed fact preserved
    assert "2:11" not in result.feedback             # fabricated pace dropped
    assert result.feedback                            # a safe fallback message is present


def test_malformed_pace_raises():
    with pytest.raises(ValueError):
        analyze(_run([(1, "5m00", 140), (2, "5:00", 140)]))
