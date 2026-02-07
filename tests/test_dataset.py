"""Tests for jfinqa.dataset — local file loading."""

from __future__ import annotations

from typing import TYPE_CHECKING

from jfinqa.dataset import load_from_file
from jfinqa.models import Subtask

if TYPE_CHECKING:
    from pathlib import Path


class TestLoadFromFile:
    def test_load_json(self, sample_questions_file: Path) -> None:
        questions = load_from_file(str(sample_questions_file))
        assert len(questions) == 5

    def test_subtask_types(self, sample_questions_file: Path) -> None:
        questions = load_from_file(str(sample_questions_file))
        subtasks = {q.subtask for q in questions}
        assert Subtask.NUMERICAL_REASONING in subtasks
        assert Subtask.CONSISTENCY_CHECKING in subtasks
        assert Subtask.TEMPORAL_REASONING in subtasks

    def test_question_fields(self, sample_questions_file: Path) -> None:
        questions = load_from_file(str(sample_questions_file))
        q = questions[0]
        assert q.id == "nr_001"
        assert q.subtask == Subtask.NUMERICAL_REASONING
        assert q.qa.answer == "25.0%"
        assert q.edinet_code == "E00001"
        assert q.table.num_rows == 4
        assert q.table.num_cols == 3

    def test_table_data(self, sample_questions_file: Path) -> None:
        questions = load_from_file(str(sample_questions_file))
        q = questions[0]
        assert q.table.headers[0] == ""
        assert q.table.rows[0][0] == "\u58f2\u4e0a\u9ad8"

    def test_format_context(self, sample_questions_file: Path) -> None:
        questions = load_from_file(str(sample_questions_file))
        ctx = questions[0].format_context()
        assert "\u9023\u7d50\u640d\u76ca\u8a08\u7b97\u66f8" in ctx
        assert "| --- |" in ctx

    def test_finqa_format_export(self, sample_questions_file: Path) -> None:
        questions = load_from_file(str(sample_questions_file))
        finqa = questions[0].to_finqa_format()
        assert finqa["id"] == "nr_001"
        assert isinstance(finqa["table"], list)
        assert len(finqa["table"]) == 5  # 1 header + 4 rows
