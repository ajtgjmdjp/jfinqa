"""Tests for Stage 4 validation answer matching.

The validation oracle must agree with the canonical scorer in
``jfinqa._metrics`` so that questions accepted by the pipeline are
also scored as correct by the published metrics.
"""

from __future__ import annotations

from jfinqa._metrics import extract_number
from scripts.pipeline.s4_validate import _numerical_match, validate_question


class TestNumericalMatchUsesCanonicalScorer:
    """The oracle must extract numbers exactly like jfinqa._metrics."""

    def test_plain_number(self) -> None:
        assert _numerical_match("133818", "133,818")

    def test_percent_format(self) -> None:
        assert _numerical_match("42.50%", "42.5%")

    def test_bai_suffix(self) -> None:
        # "倍" (times/ratio) formatted results must still parse
        assert _numerical_match("1.23倍", "1.23")

    def test_kanji_multiplier_matches_canonical(self) -> None:
        # Canonical scorer expands kanji multipliers; the oracle must too,
        # otherwise validation would accept answers the scorer rejects.
        assert extract_number("100億") == 100 * 100_000_000
        assert _numerical_match("100億", "10000000000")

    def test_million_yen_suffix(self) -> None:
        # 百万円 is a unit suffix (removesuffix), not a multiplier
        assert _numerical_match("12345百万円", "12,345")

    def test_triangle_negative(self) -> None:
        assert _numerical_match("△1,000", "-1000")

    def test_tolerance(self) -> None:
        # ANSWER_TOLERANCE is 5% relative
        assert _numerical_match("100", "104")
        assert not _numerical_match("100", "110")

    def test_non_numeric_falls_back_to_string(self) -> None:
        assert _numerical_match("増加", "増加")
        assert not _numerical_match("増加", "減少")


class TestValidateQuestion:
    def _make_q(self, program: list[str], answer: str) -> dict:
        return {
            "subtask": "numerical_reasoning",
            "qa": {
                "question": "テスト質問",
                "program": program,
                "answer": answer,
                "gold_evidence": [0],
            },
        }

    def test_numeric_pass(self) -> None:
        q = self._make_q(["subtract(100, 40)"], "60")
        passed, reason = validate_question(q)
        assert passed, reason

    def test_numeric_mismatch(self) -> None:
        q = self._make_q(["subtract(100, 40)"], "999")
        passed, reason = validate_question(q)
        assert not passed
        assert reason.startswith("answer_mismatch")

    def test_percent_answer(self) -> None:
        q = self._make_q(
            ["subtract(150, 120)", "divide(#0, 120)", "multiply(#1, 100)"],
            "25.0%",
        )
        passed, reason = validate_question(q)
        assert passed, reason
