"""Golden tests pinning the ``lm_eval_tasks/`` mirror to ``jfinqa._metrics``.

The lm-evaluation-harness task at ``lm_eval_tasks/utils.py`` duplicates
scoring logic from ``src/jfinqa/_metrics.py`` so that the task stays
self-contained inside lm-eval. These tests run a shared set of cases
through both code paths and fail if the two implementations diverge.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

from jfinqa._metrics import (
    exact_match as jfinqa_exact_match,
)
from jfinqa._metrics import (
    extract_number as jfinqa_extract_number,
)
from jfinqa._metrics import (
    normalize_answer as jfinqa_normalize,
)
from jfinqa._metrics import (
    numerical_match as jfinqa_numerical_match,
)


def _load_lm_eval_utils() -> ModuleType:
    """Load ``lm_eval_tasks/utils.py`` without relying on package layout."""
    path = Path(__file__).resolve().parent.parent / "lm_eval_tasks" / "utils.py"
    spec = importlib.util.spec_from_file_location("lm_eval_tasks_utils", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["lm_eval_tasks_utils"] = module
    spec.loader.exec_module(module)
    return module


lm_eval_utils = _load_lm_eval_utils()


GOLDEN_NORMALIZE = [
    ("  hello  ", "hello"),
    ("12,345百万円", "12345百万円"),
    ("△1,000", "-1000"),
    ("▲500", "-500"),
    (" 42.5% ", "42.5%"),
    ("改善しました", "改善"),
    ("増加した", "増加"),
]

GOLDEN_NUMERICAL_MATCH = [
    ("42.5%", "42.50%", True),
    ("24956百万円", "24956", True),
    ("△1,000", "-1000", True),
    ("100.0", "100.5", True),
    ("100.0", "102.0", False),
    ("100.0", "110.0", False),
    ("0", "0", True),
    ("0", "0.001", False),
    ("0%", "0", True),
    ("150bps", "150", True),
    ("not-a-number", "not-a-number", True),
]

GOLDEN_EXTRACT_NUMBER = [
    ("12345百万円", 12345.0),
    ("-42.5%", -42.5),
    ("100億", 1.0e10),
    ("42.5 %", 42.5),
    ("150bps", 150.0),
    ("2.5ポイント", 2.5),
    ("1,234ドル", 1234.0),
    ("0", 0.0),
    ("0%", 0.0),
    ("increase", None),
]

GOLDEN_EXTRACT_ANSWER = [
    ("Answer: 10.5", "10.5"),
    ("answer: 10.5", "10.5"),
    ("A: 10.5", "10.5"),
    ("回答: 10.5", "10.5"),
    ("回答\uff1a10.5", "10.5"),  # fullwidth colon
    ("Reasoning...\nAnswer: 42", "42"),
    ("just 10.5", "just 10.5"),
]


class TestNormalization:
    @pytest.mark.parametrize("raw, expected", GOLDEN_NORMALIZE)
    def test_jfinqa_matches_golden(self, raw: str, expected: str) -> None:
        assert jfinqa_normalize(raw) == expected

    @pytest.mark.parametrize("raw, expected", GOLDEN_NORMALIZE)
    def test_lm_eval_matches_golden(self, raw: str, expected: str) -> None:
        assert lm_eval_utils._normalize(raw) == expected

    @pytest.mark.parametrize("raw, _expected", GOLDEN_NORMALIZE)
    def test_jfinqa_and_lm_eval_agree(self, raw: str, _expected: str) -> None:
        assert jfinqa_normalize(raw) == lm_eval_utils._normalize(raw)


class TestExtractNumber:
    @pytest.mark.parametrize("raw, expected", GOLDEN_EXTRACT_NUMBER)
    def test_jfinqa_matches_golden(self, raw: str, expected: float | None) -> None:
        result = jfinqa_extract_number(raw)
        if expected is None:
            assert result is None
        else:
            assert result == pytest.approx(expected)

    @pytest.mark.parametrize("raw, expected", GOLDEN_EXTRACT_NUMBER)
    def test_lm_eval_matches_golden(self, raw: str, expected: float | None) -> None:
        result = lm_eval_utils._try_parse_number(raw)
        if expected is None:
            assert result is None
        else:
            assert result == pytest.approx(expected)


class TestNumericalMatch:
    @pytest.mark.parametrize("pred, gold, expected", GOLDEN_NUMERICAL_MATCH)
    def test_jfinqa_matches_golden(self, pred: str, gold: str, expected: bool) -> None:
        assert jfinqa_numerical_match(pred, gold) is expected

    @pytest.mark.parametrize("pred, gold, expected", GOLDEN_NUMERICAL_MATCH)
    def test_lm_eval_matches_golden(self, pred: str, gold: str, expected: bool) -> None:
        assert lm_eval_utils._numerical_match(pred, gold) is expected

    @pytest.mark.parametrize("pred, gold, _expected", GOLDEN_NUMERICAL_MATCH)
    def test_jfinqa_and_lm_eval_agree(
        self, pred: str, gold: str, _expected: bool
    ) -> None:
        assert jfinqa_numerical_match(pred, gold) == lm_eval_utils._numerical_match(
            pred, gold
        )


class TestExactMatch:
    @pytest.mark.parametrize(
        "pred, gold",
        [
            (" 42.5% ", "42.5%"),
            ("△1,000", "-1000"),
            ("改善しました", "改善"),
            ("\uff11\uff12\uff13", "123"),  # fullwidth digits → NFKC
        ],
    )
    def test_equivalent_forms_match(self, pred: str, gold: str) -> None:
        assert jfinqa_exact_match(pred, gold) is True

    @pytest.mark.parametrize(
        "pred, gold",
        [
            ("42.5%", "42.6%"),
            ("100", "200"),
        ],
    )
    def test_different_values_do_not_match(self, pred: str, gold: str) -> None:
        assert jfinqa_exact_match(pred, gold) is False


class TestExtractAnswerPattern:
    """Guards the Japanese ``回答`` label added in lm-eval v0.3.0."""

    @pytest.mark.parametrize("raw, expected", GOLDEN_EXTRACT_ANSWER)
    def test_lm_eval_parses_label(self, raw: str, expected: str) -> None:
        assert lm_eval_utils._extract_answer(raw) == expected


class TestProcessResultsIntegration:
    """End-to-end: raw model output → parsed answer → scored."""

    @pytest.mark.parametrize(
        "raw_output, gold, expected_em, expected_nm",
        [
            ("Answer: 10.5", "10.5", 1.0, 1.0),
            ("回答: 10.5", "10.5", 1.0, 1.0),
            ("回答\uff1a10.5", "10.5", 1.0, 1.0),
            ("Reasoning...\nAnswer: 42", "42", 1.0, 1.0),
            ("Answer: 100.0", "100.5", 0.0, 1.0),
            ("Answer: 100.0", "110.0", 0.0, 0.0),
            ("Answer: 24956百万円", "24956", 0.0, 1.0),
            ("Answer: △1,000", "-1000", 1.0, 1.0),
        ],
    )
    def test_scoring_pipeline(
        self,
        raw_output: str,
        gold: str,
        expected_em: float,
        expected_nm: float,
    ) -> None:
        doc = {"answer": gold}
        scores = lm_eval_utils.process_results(doc, [raw_output])
        assert scores["exact_match"] == expected_em
        assert scores["numerical_match"] == expected_nm
