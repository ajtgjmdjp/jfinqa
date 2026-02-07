"""Utility functions for lm-evaluation-harness integration.

These functions are referenced by the YAML task configs via
``!function _jfinqa_utils.<name>``.

Usage with lm-evaluation-harness::

    lm_eval --model openai \\
        --tasks jfinqa_numerical \\
        --include_path /path/to/jfinqa/lm_eval_tasks/
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any


def doc_to_text(doc: dict[str, Any]) -> str:
    """Format a dataset row as a prompt for the LLM.

    Combines pre_text, table, post_text, and question into a
    structured prompt.
    """
    parts: list[str] = []

    # Pre-text paragraphs
    pre_text = doc.get("pre_text", [])
    if pre_text:
        parts.append("\n".join(pre_text))

    # Table as markdown
    table = doc.get("table", {})
    if isinstance(table, dict):
        headers = table.get("headers", [])
        rows = table.get("rows", [])
    elif isinstance(table, list) and table:
        headers = table[0]
        rows = table[1:]
    else:
        headers = []
        rows = []

    if headers:
        header_line = "| " + " | ".join(str(h) for h in headers) + " |"
        sep_line = "| " + " | ".join("---" for _ in headers) + " |"
        row_lines = [
            "| " + " | ".join(str(c) for c in row) + " |"
            for row in rows
        ]
        parts.append("\n".join([header_line, sep_line, *row_lines]))

    # Post-text paragraphs
    post_text = doc.get("post_text", [])
    if post_text:
        parts.append("\n".join(post_text))

    # Question
    qa = doc.get("qa", {})
    question = qa.get("question", "")
    parts.append(f"Question: {question}\nAnswer:")

    return "\n\n".join(parts)


def process_results(doc: dict[str, Any], results: list[str]) -> dict[str, float]:
    """Score a model response against the gold answer.

    Returns metrics for both exact_match and numerical_match.
    """
    gold = doc.get("qa", {}).get("answer", "")
    predicted = results[0] if results else ""

    # Extract the final answer from the response
    predicted = _extract_answer(predicted)

    em = 1.0 if _normalize(predicted) == _normalize(gold) else 0.0
    nm = 1.0 if _numerical_match(predicted, gold) else 0.0

    return {"exact_match": em, "numerical_match": nm}


def _extract_answer(text: str) -> str:
    """Extract the answer from model output.

    Looks for patterns like "Answer: <value>" or just takes the
    last non-empty line.
    """
    # Look for "Answer: ..." pattern
    match = re.search(r"(?:Answer|answer|A)\s*[:：]\s*(.+)", text)
    if match:
        return match.group(1).strip()

    # Fall back to last non-empty line
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _normalize(text: str) -> str:
    """Normalize an answer for comparison."""
    s = text.strip()
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"^[△▲]", "-", s)
    s = re.sub(r"(?<=\d),(?=\d)", "", s)
    return s.lower().strip()


def _numerical_match(predicted: str, gold: str, tolerance: float = 0.01) -> bool:
    """Check numerical equivalence with tolerance."""
    pred_num = _try_parse_number(predicted)
    gold_num = _try_parse_number(gold)

    if pred_num is None or gold_num is None:
        return _normalize(predicted) == _normalize(gold)

    if gold_num == 0:
        return pred_num == 0

    return abs(pred_num - gold_num) / abs(gold_num) <= tolerance


def _try_parse_number(text: str) -> float | None:
    """Try to extract a number from text."""
    s = _normalize(text)
    # Strip common suffixes
    for suffix in ("円", "ドル", "%", "ポイント"):
        s = s.removesuffix(suffix)
    s = re.sub(r"[^\d.\-+]", "", s)
    try:
        return float(s)
    except ValueError:
        return None
