"""`run-insights` CLI — turn a run's per-km splits into objective facts + grounded feedback.

    run-insights analyze --file run.json
    run-insights demo

A run.json looks like:
    {"splits": [{"km": 1, "pace": "5:12", "hr": 148}, ...],
     "distance_km": 8.0, "elevation_m": 30}

Illustrative demo — not coaching or medical advice.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .analyzer import Coach
from .client import LLMClient
from .config import Settings
from .data.sample_runs import SAMPLE_RUNS
from .models import RunData, RunInsights

app = typer.Typer(add_completion=False, help="AI running-activity analyzer — splits, fade, HR decoupling + grounded feedback (not coaching/medical advice).")
console = Console()

_FLAG_STYLE = {
    "strong_negative_split": "green",
    "positive_split": "yellow",
    "pace_fade": "yellow",
    "hr_decoupling": "red",
}


def _print(result: RunInsights, run: RunData) -> None:
    table = Table(show_header=False, box=None, pad_edge=False)
    table.add_row("[dim]avg pace[/]", f"{result.avg_pace} /km")
    table.add_row("[dim]avg HR[/]", f"{result.avg_hr} bpm")
    table.add_row("[dim]distance[/]", f"{run.distance_km:g} km  ({run.elevation_m:g} m gain)")
    table.add_row("[dim]split[/]", f"{result.split:+.1f}%  ({'2nd half faster' if result.split < 0 else '2nd half slower'})")
    table.add_row("[dim]pace fade[/]", f"{result.fade_pct:+.1f}%  (last km vs first)")
    table.add_row("[dim]HR decoupling[/]", f"{result.decoupling_pct:+.1f}%")
    table.add_row("[dim]effort type[/]", result.effort_type)
    console.print(Panel(table, title="Run analysis", border_style="cyan"))

    if result.flags:
        for f in result.flags:
            console.print(f"[{_FLAG_STYLE.get(f.kind, 'white')}]•[/] [bold]{f.kind}[/] — {f.detail}")
    else:
        console.print("[green]•[/] nothing notable to flag.")

    if result.feedback:
        console.print(Panel(result.feedback, title="Coach", border_style="green"))
    console.print(f"\n[dim]{result.disclaimer}[/]")


def _run(run: RunData) -> None:
    settings = Settings.from_env()
    with console.status("Analyzing…"):
        result = Coach(LLMClient(settings)).insights(run)
    _print(result, run)


@app.callback()
def _root() -> None:
    """AI running-activity analyzer (illustrative demo, not coaching or medical advice)."""


@app.command()
def analyze(
    file: Path = typer.Option(None, "--file", help="Path to a run.json ({splits, distance_km, elevation_m})."),
) -> None:
    """Analyze a run from a JSON file and print facts, flags and grounded feedback."""
    if not file:
        console.print("[red]Provide --file run.json (or run `run-insights demo`).[/]")
        raise typer.Exit(1)
    run = RunData.model_validate_json(file.read_text(encoding="utf-8"))
    _run(run)


@app.command()
def demo(
    sample: str = typer.Option(
        "positive-split-fade", "--sample",
        help=f"Which baked-in synthetic run to analyze. Choices: {', '.join(SAMPLE_RUNS)}.",
    ),
) -> None:
    """Analyze a baked-in synthetic run (default: a positive-split-with-fade)."""
    run = SAMPLE_RUNS.get(sample)
    if run is None:
        console.print(f"[red]Unknown sample {sample!r}. Choices: {', '.join(SAMPLE_RUNS)}.[/]")
        raise typer.Exit(1)
    _run(run)


if __name__ == "__main__":
    app()
