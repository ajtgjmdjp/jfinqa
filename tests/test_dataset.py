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

    def test_company_name_and_scale(self, sample_questions_file: Path) -> None:
        questions = load_from_file(str(sample_questions_file))
        q = questions[0]
        assert q.company_name == "A社"
        assert q.scale == "百万円"

    def test_company_name_and_scale_default_none(
        self, sample_questions_file: Path
    ) -> None:
        questions = load_from_file(str(sample_questions_file))
        q = questions[1]  # fixture row without company_name/scale
        assert q.company_name is None
        assert q.scale is None


class TestRowToQuestion:
    """HuggingFace flat-format rows must keep all metadata fields."""

    def test_flat_row_metadata(self) -> None:
        from jfinqa.dataset import _row_to_question

        row = {
            "id": "cc_001",
            "company_name": "マルハニチロ",
            "edinet_code": "E00012",
            "source_doc_id": "S100XXXX",
            "filing_year": "2024",
            "accounting_standard": "J-GAAP",
            "scale": "百万円",
            "pre_text": ["前文"],
            "post_text": [],
            "table_headers": ["", "2024"],
            "table_rows": [["売上高", "100"]],
            "question": "質問",
            "program": ["add(1, 1)"],
            "answer": "2",
            "gold_evidence": [0],
        }
        q = _row_to_question(row, Subtask.CONSISTENCY_CHECKING)
        assert q.company_name == "マルハニチロ"
        assert q.scale == "百万円"
        assert q.edinet_code == "E00012"
        assert q.source_doc_id == "S100XXXX"
