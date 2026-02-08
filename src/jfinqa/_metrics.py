"""Answer normalization and comparison metrics for Japanese financial QA.

Handles Japan-specific number formats:
- Kanji multipliers: 千 (1e3), 百万 (1e6), 億 (1e8), 兆 (1e12)
- Triangle negative: △1,000 → -1000
- Fullwidth digits: fullwidth 123 -> 123
- Unit suffixes: 百万円, 億円, 千円, 兆円, 円, %, ポイント
- Comma-separated numbers: 1,234,567
"""

from __future__ import annotations

import re
import unicodedata

# Kanji multiplier map (value in base units)
_KANJI_MULTIPLIERS: dict[str, int] = {
    "千": 1_000,
    "百万": 1_000_000,
    "億": 100_000_000,
    "兆": 1_000_000_000_000,
}

# Unit suffixes to strip (compound units first to avoid partial matching)
_UNIT_SUFFIXES = (
    "百万円",
    "千円",
    "億円",
    "兆円",
    "円",
    "ドル",
    "ポイント",
    "pt",
    "bps",
)


def normalize_answer(answer: str) -> str:
    """Normalize an answer string for comparison.

    Applies the following transformations:
    1. Strip whitespace
    2. Normalize unicode (NFKC: fullwidth → halfwidth)
    3. Handle Japanese negative marker (△ / ▲)
    4. Remove commas from numbers
    5. Strip currency/unit suffixes
    6. Normalize percentage representation
    7. Convert to lowercase

    Args:
        answer: Raw answer string from model or gold standard.

    Returns:
        Normalized string for comparison.

    Examples:
        >>> normalize_answer("12,345百万円")
        '12345百万円'
        >>> normalize_answer("△1,000")
        '-1000'
        >>> normalize_answer(" 42.5% ")
        '42.5%'
    """
    if not answer:
        return ""

    s = answer.strip()

    # NFKC normalization: fullwidth → halfwidth digits/letters
    s = unicodedata.normalize("NFKC", s)

    # Japanese negative markers → minus sign
    s = re.sub(r"^[△▲]", "-", s)

    # Remove commas in numbers (e.g., "1,234,567" → "1234567")
    s = re.sub(r"(?<=\d),(?=\d)", "", s)

    # Normalize Japanese verb endings for categorical answers
    # e.g., "改善した" → "改善", "悪化した" → "悪化"
    # Check longer suffix first: "しました" endswith "した" is True
    if s.endswith("しました"):
        s = s.removesuffix("しました")
    elif s.endswith("した"):
        s = s.removesuffix("した")

    # Lowercase for case-insensitive comparison
    s = s.lower().strip()

    return s


def extract_number(text: str) -> float | None:
    """Extract a numeric value from a normalized answer string.

    Handles kanji multipliers and percentage notation.

    Args:
        text: A normalized answer string.

    Returns:
        The numeric value, or ``None`` if not parseable.

    Examples:
        >>> extract_number("12345百万円")
        12345.0
        >>> extract_number("-42.5%")
        -42.5
        >>> extract_number("増加")
    """
    s = normalize_answer(text)
    if not s:
        return None

    # Strip unit suffixes for parsing
    for suffix in _UNIT_SUFFIXES:
        s = s.removesuffix(suffix)

    # Check for kanji multiplier (e.g., "100億" → 100 * 1e8)
    for kanji, multiplier in _KANJI_MULTIPLIERS.items():
        if kanji in s:
            num_part = s.replace(kanji, "").strip()
            # Remove remaining unit text
            num_part = re.sub(r"[^\d.\-+]", "", num_part)
            try:
                return float(num_part) * multiplier
            except ValueError:
                return None

    # Strip % for percentage values (keep as-is for comparison)
    is_percent = s.endswith("%")
    if is_percent:
        s = s.removesuffix("%")

    # Try to parse the remaining string as a number
    s = re.sub(r"[^\d.\-+]", "", s)
    try:
        return float(s)
    except ValueError:
        return None


def exact_match(predicted: str, gold: str) -> bool:
    """Check if two answers match after normalization.

    Args:
        predicted: Model's predicted answer.
        gold: Gold-standard answer.

    Returns:
        ``True`` if answers match after normalization.

    Examples:
        >>> exact_match("42.5%", " 42.5 % ")
        True
        >>> exact_match("△1,000", "-1000")
        True
    """
    return normalize_answer(predicted) == normalize_answer(gold)


def numerical_match(
    predicted: str,
    gold: str,
    *,
    rel_tolerance: float = 0.01,
) -> bool:
    """Check if two answers are numerically equivalent.

    Falls back to :func:`exact_match` if either value cannot be
    parsed as a number.

    Args:
        predicted: Model's predicted answer.
        gold: Gold-standard answer.
        rel_tolerance: Relative tolerance for floating-point
            comparison (default: 1%).

    Returns:
        ``True`` if answers match numerically within tolerance.

    Examples:
        >>> numerical_match("42.5%", "42.50%")
        True
        >>> numerical_match("24956百万円", "24956")
        True
    """
    pred_num = extract_number(predicted)
    gold_num = extract_number(gold)

    if pred_num is None or gold_num is None:
        return exact_match(predicted, gold)

    if gold_num == 0:
        return pred_num == 0

    rel_diff = abs(pred_num - gold_num) / abs(gold_num)
    return rel_diff <= rel_tolerance
