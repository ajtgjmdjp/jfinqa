"""Shared test fixtures for jfinqa."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jfinqa.models import QAPair, Question, Subtask, Table

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def sample_table() -> Table:
    return Table(
        headers=["", "2024", "2023"],
        rows=[
            ["Revenue", "1500000", "1200000"],
            ["Profit", "200000", "150000"],
        ],
    )


@pytest.fixture()
def sample_qa() -> QAPair:
    return QAPair(
        question="What is the revenue growth rate?",
        program=["subtract(1500000, 1200000)", "divide(#0, 1200000)"],
        answer="25.0%",
        gold_evidence=[0],
    )


@pytest.fixture()
def sample_question(sample_table: Table, sample_qa: QAPair) -> Question:
    return Question(
        id="nr_001",
        subtask=Subtask.NUMERICAL_REASONING,
        pre_text=["The following is a summary."],
        post_text=["Revenue increased year over year."],
        table=sample_table,
        qa=sample_qa,
        edinet_code="E02144",
        filing_year="2024",
    )


@pytest.fixture()
def sample_questions_file() -> Path:
    return FIXTURES_DIR / "sample_questions.json"


@pytest.fixture()
def sample_questions_list(sample_questions_file: Path) -> list[Question]:
    """Load sample questions from fixture file."""
    from jfinqa.dataset import load_from_file

    return load_from_file(str(sample_questions_file))


@pytest.fixture()
def sample_questions_raw(sample_questions_file: Path) -> list[dict]:
    with open(sample_questions_file, encoding="utf-8") as f:
        return json.load(f)
