"""Tests for jfinqa._metrics — Japanese financial number normalization."""

from __future__ import annotations

import pytest

from jfinqa._metrics import (
    exact_match,
    extract_number,
    normalize_answer,
    numerical_match,
)


class TestNormalizeAnswer:
    def test_strip_whitespace(self) -> None:
        assert normalize_answer("  42.5%  ") == "42.5%"

    def test_fullwidth_digits(self) -> None:
        assert normalize_answer("\uff11\uff12\uff13") == "123"

    def test_triangle_negative(self) -> None:
        assert normalize_answer("\u25b31,000") == "-1000"

    def test_triangle_filled(self) -> None:
        assert normalize_answer("\u25b21,000") == "-1000"

    def test_remove_commas(self) -> None:
        assert normalize_answer("1,234,567") == "1234567"

    def test_lowercase(self) -> None:
        assert normalize_answer("IFRS") == "ifrs"

    def test_empty(self) -> None:
        assert normalize_answer("") == ""


class TestExtractNumber:
    def test_integer(self) -> None:
        assert extract_number("12345") == 12345.0

    def test_float(self) -> None:
        assert extract_number("42.5") == 42.5

    def test_negative(self) -> None:
        assert extract_number("-100") == -100.0

    def test_percentage(self) -> None:
        assert extract_number("42.5%") == 42.5

    def test_yen_suffix(self) -> None:
        assert extract_number("1000\u5186") == 1000.0

    def test_financial_unit_million_yen(self) -> None:
        # "百万円" is a reporting unit label, not a multiplier
        assert extract_number("100\u767e\u4e07\u5186") == 100.0

    def test_financial_unit_oku_yen(self) -> None:
        assert extract_number("50\u5104\u5186") == 50.0

    def test_financial_unit_cho_yen(self) -> None:
        assert extract_number("1.5\u5146\u5186") == 1.5

    def test_kanji_multiplier_without_yen(self) -> None:
        # Bare kanji multipliers (no 円) still apply multiplication
        assert extract_number("100\u767e\u4e07") == 100_000_000.0
        assert extract_number("50\u5104") == 5_000_000_000.0
        assert extract_number("1.5\u5146") == 1_500_000_000_000.0

    def test_non_numeric(self) -> None:
        assert extract_number("\u5897\u52a0") is None

    def test_empty(self) -> None:
        assert extract_number("") is None

    def test_triangle_with_financial_unit(self) -> None:
        # △500百万円 → -500 (百万円 stripped as unit)
        assert extract_number("\u25b3500\u767e\u4e07\u5186") == -500.0

    def test_triangle_with_kanji_multiplier(self) -> None:
        # △500百万 → -500,000,000 (百万 as multiplier)
        assert extract_number("\u25b3500\u767e\u4e07") == -500_000_000.0


class TestExactMatch:
    def test_same(self) -> None:
        assert exact_match("42.5%", "42.5%") is True

    def test_whitespace(self) -> None:
        assert exact_match("42.5%", " 42.5% ") is True

    def test_triangle_vs_minus(self) -> None:
        assert exact_match("\u25b31,000", "-1000") is True

    def test_different(self) -> None:
        assert exact_match("42.5%", "43.0%") is False


class TestNumericalMatch:
    def test_exact_numbers(self) -> None:
        assert numerical_match("42.5%", "42.50%") is True

    def test_within_tolerance(self) -> None:
        assert numerical_match("42.5", "42.0", rel_tolerance=0.02) is True

    def test_outside_tolerance(self) -> None:
        assert numerical_match("42.5", "40.0", rel_tolerance=0.01) is False

    @pytest.mark.parametrize(
        ("pred", "gold"),
        [
            ("24956\u767e\u4e07\u5186", "24956"),  # unit label stripped
            ("\u25b31,000", "-1000"),
            ("25.0%", "25%"),
        ],
    )
    def test_japanese_formats(self, pred: str, gold: str) -> None:
        assert numerical_match(pred, gold) is True

    def test_zero_gold(self) -> None:
        assert numerical_match("0", "0") is True
        assert numerical_match("1", "0") is False

    def test_non_numeric_fallback(self) -> None:
        assert numerical_match("consistent", "consistent") is True
        assert numerical_match("consistent", "inconsistent") is False
