"""Tests for jfinqa.evaluate."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from jfinqa.evaluate import evaluate

if TYPE_CHECKING:
    from jfinqa.models import Question


class TestEvaluate:
    def test_with_predictions(self, sample_questions_list: list[Question]) -> None:
        preds = {q.id: q.qa.answer for q in sample_questions_list}
        result = evaluate(sample_questions_list, predictions=preds)
        assert result.accuracy == 1.0
        assert result.total == len(sample_questions_list)
        assert result.correct == result.total

    def test_with_model_fn(self, sample_questions_list: list[Question]) -> None:
        answers = {q.id: q.qa.answer for q in sample_questions_list}

        def model_fn(question: str, context: str) -> str:
            for q in sample_questions_list:
                if q.qa.question == question:
                    return answers[q.id]
            return ""

        result = evaluate(sample_questions_list, model_fn=model_fn)
        assert result.accuracy == 1.0

    def test_wrong_predictions(self, sample_questions_list: list[Question]) -> None:
        preds = {q.id: "WRONG" for q in sample_questions_list}
        result = evaluate(sample_questions_list, predictions=preds)
        assert result.accuracy == 0.0
        assert result.correct == 0

    def test_missing_predictions(self, sample_questions_list: list[Question]) -> None:
        result = evaluate(sample_questions_list, predictions={})
        assert result.accuracy == 0.0

    def test_per_subtask_breakdown(self, sample_questions_list: list[Question]) -> None:
        preds = {q.id: q.qa.answer for q in sample_questions_list}
        result = evaluate(sample_questions_list, predictions=preds)
        assert "numerical_reasoning" in result.by_subtask
        nr = result.by_subtask["numerical_reasoning"]
        assert nr.accuracy == 1.0
        assert nr.total == 2

    def test_exact_match_mode(self, sample_questions_list: list[Question]) -> None:
        preds = {q.id: q.qa.answer for q in sample_questions_list}
        result = evaluate(sample_questions_list, predictions=preds, match_mode="exact")
        assert result.accuracy == 1.0

    def test_no_input_raises(self, sample_questions_list: list[Question]) -> None:
        with pytest.raises(ValueError, match="Provide either"):
            evaluate(sample_questions_list)

    def test_both_inputs_raises(self, sample_questions_list: list[Question]) -> None:
        with pytest.raises(ValueError, match="Provide only one"):
            evaluate(
                sample_questions_list,
                predictions={},
                model_fn=lambda q, c: "",
            )

    def test_summary_output(self, sample_questions_list: list[Question]) -> None:
        preds = {q.id: q.qa.answer for q in sample_questions_list}
        result = evaluate(sample_questions_list, predictions=preds)
        summary = result.summary()
        assert "100.0%" in summary
        assert "jfinqa" in summary


class TestEvaluateEmpty:
    def test_empty_questions(self) -> None:
        result = evaluate([], predictions={})
        assert result.total == 0
        assert result.accuracy == 0.0
