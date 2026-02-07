"""Tests for jfinqa.models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from jfinqa.models import (
    BenchmarkResult,
    QAPair,
    Question,
    QuestionResult,
    Subtask,
    SubtaskResult,
    Table,
)


class TestSubtask:
    def test_values(self) -> None:
        assert Subtask.NUMERICAL_REASONING.value == "numerical_reasoning"
        assert Subtask.CONSISTENCY_CHECKING.value == "consistency_checking"
        assert Subtask.TEMPORAL_REASONING.value == "temporal_reasoning"

    def test_all(self) -> None:
        assert len(Subtask.all()) == 3

    def test_from_string(self) -> None:
        assert Subtask("numerical_reasoning") == Subtask.NUMERICAL_REASONING


class TestTable:
    def test_finqa_roundtrip(self, sample_table: Table) -> None:
        finqa = sample_table.to_finqa_format()
        restored = Table.from_finqa_format(finqa)
        assert restored.headers == sample_table.headers
        assert restored.rows == sample_table.rows

    def test_finqa_empty(self) -> None:
        t = Table.from_finqa_format([])
        assert t.headers == []
        assert t.rows == []

    def test_markdown(self, sample_table: Table) -> None:
        md = sample_table.to_markdown()
        assert "| Revenue |" in md
        assert "| --- |" in md

    def test_properties(self, sample_table: Table) -> None:
        assert sample_table.num_rows == 2
        assert sample_table.num_cols == 3

    def test_frozen(self, sample_table: Table) -> None:
        with pytest.raises(ValidationError):
            sample_table.headers = ["a", "b"]  # type: ignore[misc]


class TestQAPair:
    def test_fields(self, sample_qa: QAPair) -> None:
        assert sample_qa.question == "What is the revenue growth rate?"
        assert sample_qa.answer == "25.0%"
        assert len(sample_qa.program) == 2

    def test_defaults(self) -> None:
        qa = QAPair(question="test?", answer="42")
        assert qa.program == []
        assert qa.gold_evidence == []


class TestQuestion:
    def test_format_context(self, sample_question: Question) -> None:
        ctx = sample_question.format_context()
        assert "The following is a summary." in ctx
        assert "| Revenue |" in ctx
        assert "Revenue increased" in ctx

    def test_finqa_roundtrip(self, sample_question: Question) -> None:
        finqa = sample_question.to_finqa_format()
        assert finqa["id"] == "nr_001"
        assert finqa["qa"]["answer"] == "25.0%"

        restored = Question.from_finqa_format(finqa)
        assert restored.id == sample_question.id
        assert restored.qa.answer == sample_question.qa.answer
        assert restored.table.headers == sample_question.table.headers

    def test_metadata(self, sample_question: Question) -> None:
        assert sample_question.edinet_code == "E02144"
        assert sample_question.filing_year == "2024"

    def test_frozen(self, sample_question: Question) -> None:
        with pytest.raises(ValidationError):
            sample_question.id = "new_id"  # type: ignore[misc]


class TestResults:
    def test_subtask_result(self) -> None:
        sr = SubtaskResult(accuracy=0.8, total=10, correct=8)
        assert sr.accuracy == 0.8

    def test_benchmark_result_summary(self) -> None:
        result = BenchmarkResult(
            accuracy=0.75,
            total=4,
            correct=3,
            by_subtask={
                "numerical_reasoning": SubtaskResult(accuracy=1.0, total=2, correct=2),
                "temporal_reasoning": SubtaskResult(accuracy=0.5, total=2, correct=1),
            },
            results=[
                QuestionResult(
                    question_id="q1",
                    subtask=Subtask.NUMERICAL_REASONING,
                    predicted="25%",
                    gold="25%",
                    correct=True,
                ),
            ],
        )
        summary = result.summary()
        assert "75.0%" in summary
        assert "numerical_reasoning" in summary
