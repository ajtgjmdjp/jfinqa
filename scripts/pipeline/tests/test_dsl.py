"""Tests for the DSL interpreter."""

from __future__ import annotations

import math

import pytest

from scripts.pipeline.dsl import DSLError, execute_program


class TestBasicOperations:
    def test_add(self) -> None:
        assert execute_program(["add(10, 20)"]) == 30

    def test_subtract(self) -> None:
        assert execute_program(["subtract(100, 40)"]) == 60

    def test_multiply(self) -> None:
        assert execute_program(["multiply(5, 8)"]) == 40

    def test_divide(self) -> None:
        assert execute_program(["divide(100, 4)"]) == 25.0

    def test_divide_by_zero(self) -> None:
        result = execute_program(["divide(100, 0)"])
        assert isinstance(result, float) and math.isinf(result)


class TestReferences:
    def test_step_reference(self) -> None:
        result = execute_program(
            [
                "subtract(1500000, 1200000)",
                "divide(#0, 1200000)",
                "multiply(#1, 100)",
            ]
        )
        assert isinstance(result, float) and abs(result - 25.0) < 0.001

    def test_multi_reference(self) -> None:
        result = execute_program(
            [
                "add(100, 200)",
                "add(300, 400)",
                "add(#0, #1)",
            ]
        )
        assert result == 1000


class TestComparison:
    def test_eq_true(self) -> None:
        result = execute_program(["add(50000, 80000)", "eq(#0, 130000)"])
        assert result is True

    def test_eq_false(self) -> None:
        result = execute_program(["add(50000, 80000)", "eq(#0, 999999)"])
        assert result is False

    def test_greater(self) -> None:
        assert execute_program(["greater(100, 50)"]) is True
        assert execute_program(["greater(50, 100)"]) is False


class TestMinMax:
    def test_min(self) -> None:
        result = execute_program(["min(500, 450, 380, 420, 400)"])
        assert result == 380

    def test_max(self) -> None:
        result = execute_program(["max(500, 450, 380, 420, 400)"])
        assert result == 500


class TestLargeNumbers:
    def test_large_integers(self) -> None:
        """DSL programs use raw integers without commas."""
        result = execute_program(["add(1000, 2000)"])
        assert result == 3000

    def test_negative_number(self) -> None:
        result = execute_program(["add(25000, -15000)"])
        assert result == 10000


class TestErrors:
    def test_empty_program(self) -> None:
        with pytest.raises(DSLError, match="Empty"):
            execute_program([])

    def test_unknown_operation(self) -> None:
        with pytest.raises(DSLError, match="unknown"):
            execute_program(["foobar(1, 2)"])

    def test_bad_reference(self) -> None:
        with pytest.raises(DSLError, match="argument error"):
            execute_program(["add(#5, 10)"])

    def test_invalid_syntax(self) -> None:
        with pytest.raises(DSLError, match="cannot parse"):
            execute_program(["not a valid step"])


class TestRealWorldExamples:
    """Examples from the sample_questions.json fixture."""

    def test_revenue_growth_rate(self) -> None:
        result = execute_program(
            [
                "subtract(1500000, 1200000)",
                "divide(#0, 1200000)",
                "multiply(#1, 100)",
            ]
        )
        assert isinstance(result, float) and abs(result - 25.0) < 0.01

    def test_operating_margin(self) -> None:
        result = execute_program(["divide(8000, 50000)", "multiply(#0, 100)"])
        assert isinstance(result, float) and abs(result - 16.0) < 0.01

    def test_consistency_check(self) -> None:
        result = execute_program(["add(50000, 80000)", "eq(#0, 130000)"])
        assert result is True

    def test_fcf_calculation(self) -> None:
        result = execute_program(["add(25000, -15000)"])
        assert result == 10000
