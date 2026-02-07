"""CLI orchestrator for the jfinqa data construction pipeline.

Usage::

    # Run all stages
    python scripts/pipeline/run_pipeline.py

    # Run a specific stage
    python scripts/pipeline/run_pipeline.py --stage 1

    # Custom data directory
    python scripts/pipeline/run_pipeline.py --data-dir /path/to/data
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from loguru import logger


@click.command()
@click.option(
    "--stage",
    type=click.Choice(["1", "2", "4", "all"]),
    default="all",
    help="Which stage to run. Stage 3 is done in Claude Code.",
)
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=None,
    help="Override the data directory.",
)
def main(stage: str, data_dir: Path | None) -> None:
    """Run the jfinqa data construction pipeline."""
    logger.remove()
    logger.add(
        sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level:<7} | {message}"
    )

    if data_dir:
        from scripts.pipeline import config

        config.RAW_DIR = data_dir / "raw"
        config.CONTEXTS_DIR = data_dir / "contexts"
        config.GENERATED_DIR = data_dir / "generated"
        config.FINAL_DIR = data_dir / "final"

    if stage in ("1", "all"):
        logger.info("=" * 60)
        logger.info("STAGE 1: Collecting data from EDINET")
        logger.info("=" * 60)
        from scripts.pipeline.s1_collect import run as run_s1

        run_s1()

    if stage in ("2", "all"):
        logger.info("=" * 60)
        logger.info("STAGE 2: Transforming to table contexts")
        logger.info("=" * 60)
        from scripts.pipeline.s2_transform import run as run_s2

        run_s2()

    if stage == "all":
        logger.info("=" * 60)
        logger.info("STAGE 3: QA generation (run in Claude Code)")
        logger.info("  Skipping — this stage is done interactively.")
        logger.info("  See: scripts/data/contexts/ for input files")
        logger.info("  Save generated QAs to: scripts/data/generated/")
        logger.info("=" * 60)

    if stage in ("4", "all"):
        logger.info("=" * 60)
        logger.info("STAGE 4: Validating and producing final dataset")
        logger.info("=" * 60)
        from scripts.pipeline.s4_validate import run as run_s4

        run_s4()

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    main()
