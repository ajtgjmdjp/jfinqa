"""Command-line interface for jfinqa.

Provides commands:
- ``jfinqa evaluate``: Run evaluation with predictions file
- ``jfinqa inspect``: Browse and inspect dataset questions
"""

from __future__ import annotations

import json
import sys

import click
from loguru import logger


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """Japanese Financial QA Benchmark tools."""
    level = "DEBUG" if verbose else "INFO"
    logger.remove()
    logger.add(
        sys.stderr,
        level=level,
        format="{time:HH:mm:ss} | {level:<7} | {message}",
    )


@cli.command()
@click.option(
    "--subtask",
    "-s",
    default=None,
    type=click.Choice(
        ["numerical_reasoning", "consistency_checking", "temporal_reasoning"]
    ),
    help="Filter to a specific subtask.",
)
@click.option(
    "--predictions",
    "-p",
    required=True,
    type=click.Path(exists=True),
    help="JSON file mapping question IDs to predicted answers.",
)
@click.option(
    "--data",
    "-d",
    default=None,
    type=click.Path(exists=True),
    help="Local data file (JSON/JSONL). If omitted, loads from HuggingFace.",
)
@click.option(
    "--match-mode",
    "-m",
    default="numerical",
    type=click.Choice(["exact", "numerical"]),
    help="Answer matching strategy.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    type=click.Path(),
    help="Save detailed results to JSON file.",
)
def evaluate(
    subtask: str | None,
    predictions: str,
    data: str | None,
    match_mode: str,
    output: str | None,
) -> None:
    """Evaluate model predictions against gold answers.

    Examples:

        jfinqa evaluate -p predictions.json

        jfinqa evaluate -s numerical_reasoning -p preds.json -d local.json
    """
    from jfinqa.dataset import load_dataset, load_from_file
    from jfinqa.evaluate import evaluate as run_eval

    # Load predictions
    with open(predictions, encoding="utf-8") as f:
        preds: dict[str, str] = json.load(f)

    # Load questions
    if data:
        questions = load_from_file(data)
    else:
        questions = load_dataset(subtask)

    if subtask and data:
        questions = [q for q in questions if q.subtask.value == subtask]

    if not questions:
        click.echo("No questions found.", err=True)
        sys.exit(1)

    click.echo(f"Evaluating {len(questions)} questions...")
    result = run_eval(
        questions,
        predictions=preds,
        match_mode=match_mode,
    )

    click.echo(result.summary())

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(
                result.model_dump(mode="json"),
                f,
                ensure_ascii=False,
                indent=2,
            )
        click.echo(f"\nDetailed results saved to {output}")


@cli.command()
@click.option(
    "--subtask",
    "-s",
    default=None,
    type=click.Choice(
        ["numerical_reasoning", "consistency_checking", "temporal_reasoning"]
    ),
    help="Filter to a specific subtask.",
)
@click.option(
    "--data",
    "-d",
    default=None,
    type=click.Path(exists=True),
    help="Local data file (JSON/JSONL). If omitted, loads from HuggingFace.",
)
@click.option(
    "--limit",
    "-n",
    default=5,
    help="Number of questions to display.",
)
@click.option(
    "--json-output",
    "-j",
    "as_json",
    is_flag=True,
    help="Output as JSON.",
)
def inspect(
    subtask: str | None,
    data: str | None,
    limit: int,
    as_json: bool,
) -> None:
    """Inspect dataset questions.

    Examples:

        jfinqa inspect -s numerical_reasoning -n 3

        jfinqa inspect -d local_data.json --json
    """
    from jfinqa.dataset import load_dataset, load_from_file

    if data:
        questions = load_from_file(data)
    else:
        questions = load_dataset(subtask)

    if subtask and data:
        questions = [q for q in questions if q.subtask.value == subtask]

    questions = questions[:limit]

    if as_json:
        click.echo(
            json.dumps(
                [q.model_dump(mode="json") for q in questions],
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    for q in questions:
        click.echo(f"{'=' * 60}")
        click.echo(f"ID: {q.id}  |  Subtask: {q.subtask.value}")
        click.echo(f"Question: {q.qa.question}")
        click.echo(f"Answer: {q.qa.answer}")
        if q.qa.program:
            click.echo(f"Program: {' → '.join(q.qa.program)}")
        click.echo(f"Table: {q.table.num_rows} rows x {q.table.num_cols} cols")
        if q.edinet_code:
            click.echo(f"Source: {q.edinet_code} ({q.filing_year})")
        click.echo()
