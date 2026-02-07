"""FinQA-compatible DSL interpreter for answer verification.

Executes a sequence of arithmetic operations and returns the final result.
Used in Stage 4 to verify that generated QA pairs have correct answers.

Example::

    >>> execute_program(["subtract(1500000, 1200000)", "divide(#0, 1200000)",
    ...                   "multiply(#1, 100)"])
    25.0
"""

from __future__ import annotations

import math
import re
from typing import Any

# ---------------------------------------------------------------------------
# Operations
# ---------------------------------------------------------------------------

_OPS: dict[str, Any] = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b if b != 0 else math.inf,
    "exp": lambda a, b: a**b,
    "greater": lambda a, b: a > b,
    "less": lambda a, b: a < b,
    "eq": lambda a, b: (
        abs(a - b) < 0.001
        if isinstance(a, (int, float)) and isinstance(b, (int, float))
        else a == b
    ),
    "min": lambda *args: min(args),
    "max": lambda *args: max(args),
    "abs": lambda a: abs(a),
    "round": lambda a, b=0: round(a, int(b)),
}

# Pattern to match: "operation(arg1, arg2, ...)"
_STEP_RE = re.compile(r"^(\w+)\((.+)\)$")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def execute_program(program: list[str]) -> float | bool | str:
    """Execute a FinQA DSL program and return the final result.

    Args:
        program: List of DSL operation strings.

    Returns:
        The result of the last operation.

    Raises:
        DSLError: If a step cannot be parsed or executed.
    """
    if not program:
        msg = "Empty program"
        raise DSLError(msg)

    results: list[Any] = []

    for i, step in enumerate(program):
        step = step.strip()
        match = _STEP_RE.match(step)
        if not match:
            msg = f"Step {i}: cannot parse '{step}'"
            raise DSLError(msg)

        op_name = match.group(1)
        args_str = match.group(2)

        if op_name not in _OPS:
            msg = f"Step {i}: unknown operation '{op_name}'"
            raise DSLError(msg)

        try:
            args = [_resolve_arg(a.strip(), results) for a in _split_args(args_str)]
        except (ValueError, IndexError) as e:
            msg = f"Step {i}: argument error in '{step}': {e}"
            raise DSLError(msg) from e

        try:
            result = _OPS[op_name](*args)
        except (TypeError, ZeroDivisionError, OverflowError) as e:
            msg = f"Step {i}: execution error in '{step}': {e}"
            raise DSLError(msg) from e

        results.append(result)

    last: float | bool | str = results[-1]
    return last


class DSLError(Exception):
    """Raised when a DSL program cannot be executed."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_arg(arg: str, results: list[Any]) -> Any:
    """Resolve a DSL argument: #N reference or literal value."""
    if arg.startswith("#"):
        idx = int(arg[1:])
        if idx < 0 or idx >= len(results):
            msg = f"Invalid reference {arg} (only {len(results)} results available)"
            raise IndexError(msg)
        return results[idx]

    # Boolean literals
    if arg.lower() == "true":
        return True
    if arg.lower() == "false":
        return False

    # Try numeric
    cleaned = arg.replace(",", "")
    try:
        if "." in cleaned:
            return float(cleaned)
        return int(cleaned)
    except ValueError:
        pass

    # Return as string
    return arg


def _split_args(args_str: str) -> list[str]:
    """Split comma-separated arguments, respecting nested parentheses."""
    args: list[str] = []
    depth = 0
    current = ""

    for ch in args_str:
        if ch == "(":
            depth += 1
            current += ch
        elif ch == ")":
            depth -= 1
            current += ch
        elif ch == "," and depth == 0:
            args.append(current.strip())
            current = ""
        else:
            current += ch

    if current.strip():
        args.append(current.strip())

    return args
