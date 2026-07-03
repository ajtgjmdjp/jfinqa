"""Smoke tests for jfinqa._prompts templates.

The prompt templates must instruct answer formats that match the gold
answers in the dataset. In particular, consistency_checking gold
answers are ~92% numeric and the boolean subset uses Japanese
はい/いいえ — never English "Consistent"/"Inconsistent".
"""

from __future__ import annotations

import pytest

from jfinqa._prompts import (
    CONSISTENCY_CHECKING_PROMPT,
    NUMERICAL_REASONING_PROMPT,
    PROMPTS,
    SYSTEM_PROMPT,
    TEMPORAL_REASONING_PROMPT,
    format_prompt,
)


class TestTemplateStructure:
    def test_all_subtasks_mapped(self) -> None:
        assert set(PROMPTS) == {
            "numerical_reasoning",
            "consistency_checking",
            "temporal_reasoning",
        }

    @pytest.mark.parametrize("template", list(PROMPTS.values()))
    def test_placeholders_present(self, template: str) -> None:
        assert "{context}" in template
        assert "{question}" in template

    @pytest.mark.parametrize("subtask", list(PROMPTS))
    def test_format_prompt(self, subtask: str) -> None:
        result = format_prompt(subtask, "QUESTION_X", "CONTEXT_Y")
        assert "QUESTION_X" in result
        assert "CONTEXT_Y" in result
        assert "{" not in result.replace("{}", "")

    def test_unknown_subtask_falls_back(self) -> None:
        result = format_prompt("unknown", "Q", "C")
        assert result == NUMERICAL_REASONING_PROMPT.format(question="Q", context="C")

    def test_system_prompt_nonempty(self) -> None:
        assert SYSTEM_PROMPT.strip()


class TestConsistencyCheckingAnswerFormat:
    """CC gold answers are numeric or はい/いいえ; the template must say so."""

    def test_mentions_japanese_boolean(self) -> None:
        assert "はい" in CONSISTENCY_CHECKING_PROMPT
        assert "いいえ" in CONSISTENCY_CHECKING_PROMPT

    def test_mentions_numeric_answers(self) -> None:
        assert "numeric" in CONSISTENCY_CHECKING_PROMPT.lower()

    def test_no_english_consistency_labels(self) -> None:
        # Gold answers never use these labels; instructing them would
        # guarantee a scoring mismatch.
        assert '"Consistent"' not in CONSISTENCY_CHECKING_PROMPT
        assert '"Inconsistent"' not in CONSISTENCY_CHECKING_PROMPT
        assert "Inconsistent:" not in CONSISTENCY_CHECKING_PROMPT


class TestTemporalReasoningTemplate:
    def test_mentions_time(self) -> None:
        assert "over time" in TEMPORAL_REASONING_PROMPT
