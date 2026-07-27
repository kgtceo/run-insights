"""Three synthetic runs with known patterns — used by the CLI demo, the API /api/samples, and as
readable fixtures. Synthetic data only; not real athlete data.

  • negative-split-10k  — 2nd half faster than the 1st, HR steady (a well-paced easy run).
  • positive-split-fade — 2nd half slower and the last km fades hard (went out too fast).
  • hr-drift-tempo       — pace roughly steady but HR climbs through the run (aerobic decoupling).
"""

from __future__ import annotations

from ..models import RunData, Split


def _run(splits: list[tuple[int, str, int]], distance_km: float, elevation_m: float) -> RunData:
    return RunData(
        splits=[Split(km=k, pace=p, hr=h) for k, p, h in splits],
        distance_km=distance_km,
        elevation_m=elevation_m,
    )


# A well-paced easy run: the second half is a touch quicker, heart rate barely moves.
NEGATIVE_SPLIT_10K = _run(
    [
        (1, "5:32", 142),
        (2, "5:30", 144),
        (3, "5:28", 145),
        (4, "5:29", 146),
        (5, "5:18", 146),
        (6, "5:16", 147),
        (7, "5:15", 148),
        (8, "5:12", 149),
    ],
    distance_km=8.0,
    elevation_m=25.0,
)

# Went out too fast: the second half slows and the last km fades badly.
POSITIVE_SPLIT_FADE = _run(
    [
        (1, "4:58", 150),
        (2, "5:00", 152),
        (3, "5:04", 154),
        (4, "5:08", 156),
        (5, "5:20", 159),
        (6, "5:28", 161),
        (7, "5:36", 163),
        (8, "5:44", 165),
    ],
    distance_km=8.0,
    elevation_m=40.0,
)

# Pace held roughly steady, but heart rate climbs through the run — classic aerobic decoupling.
HR_DRIFT_TEMPO = _run(
    [
        (1, "5:08", 150),
        (2, "5:10", 153),
        (3, "5:09", 156),
        (4, "5:10", 159),
        (5, "5:11", 164),
        (6, "5:10", 168),
        (7, "5:12", 171),
        (8, "5:11", 174),
    ],
    distance_km=8.0,
    elevation_m=30.0,
)

SAMPLE_RUNS: dict[str, RunData] = {
    "negative-split-10k": NEGATIVE_SPLIT_10K,
    "positive-split-fade": POSITIVE_SPLIT_FADE,
    "hr-drift-tempo": HR_DRIFT_TEMPO,
}


def sample_by_name(name: str) -> RunData:
    try:
        return SAMPLE_RUNS[name]
    except KeyError as exc:
        raise KeyError(f"unknown sample {name!r}; choices: {', '.join(SAMPLE_RUNS)}") from exc
