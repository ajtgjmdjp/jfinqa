"""Stage 2: Transform raw EDINET data into table contexts for QA generation.

Converts the raw StatementData items (XBRL element/value dicts) into
human-readable Japanese financial tables with pre_text/post_text and
preserved raw_values for answer verification.

Usage::

    python -m scripts.pipeline.s2_transform
    # or via run_pipeline.py --stage 2
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from loguru import logger

from scripts.pipeline.config import (
    CONTEXTS_DIR,
    POST_TEXT_TEMPLATES,
    PRE_TEXT_TEMPLATES,
    RAW_DIR,
)
from scripts.pipeline.element_map import (
    BS_DISPLAY_ORDER,
    BS_ELEMENTS,
    CF_DISPLAY_ORDER,
    CF_ELEMENTS,
    PL_DISPLAY_ORDER,
    PL_ELEMENTS,
    to_japanese,
)

# ---------------------------------------------------------------------------
# Number formatting
# ---------------------------------------------------------------------------


def _choose_scale(values: list[int | float]) -> tuple[str, int]:
    """Choose display scale based on the magnitude of values.

    Returns (scale_label, divisor).
    """
    if not values:
        return ("円", 1)

    max_abs = max(abs(v) for v in values if isinstance(v, (int, float)))

    if max_abs >= 1_000_000_000_000:  # 1兆以上
        return ("百万円", 1_000_000)
    if max_abs >= 100_000_000:  # 1億以上
        return ("百万円", 1_000_000)
    if max_abs >= 1_000_000:  # 100万以上
        return ("千円", 1_000)
    return ("円", 1)


def _format_number(value: int | float, divisor: int) -> str:
    """Format a numeric value for table display."""
    if not isinstance(value, (int, float)):
        return str(value)

    scaled = value / divisor
    is_negative = scaled < 0
    abs_val = abs(scaled)

    if abs_val == int(abs_val):
        formatted = f"{int(abs_val):,}"
    else:
        formatted = f"{abs_val:,.1f}"

    if is_negative:
        return f"\u25b3{formatted}"  # △ prefix for negative
    return formatted


# ---------------------------------------------------------------------------
# Statement extraction helpers
# ---------------------------------------------------------------------------


def _extract_items(
    raw_items: list[dict[str, Any]] | None,
    element_map: dict[str, str],
    display_order: list[str],
) -> list[tuple[str, str, int | float]]:
    """Extract and order financial line items from raw data.

    Returns list of (japanese_label, element_name, raw_value).
    """
    if not raw_items:
        return []

    # Build lookup: element_name -> value
    available: dict[str, int | float] = {}
    for item in raw_items:
        elem = item.get("element", "")
        val = item.get("value")
        if elem and isinstance(val, (int, float)):
            available[elem] = val
        # Also try the label field (TSV files may have labels)
        label = item.get("label", "")
        if label and isinstance(val, (int, float)):
            available[label] = val

    # Pick items in display order
    result: list[tuple[str, str, int | float]] = []
    seen_labels: set[str] = set()

    for elem_name in display_order:
        if elem_name in available:
            jp_label = element_map.get(elem_name, elem_name)
            if jp_label not in seen_labels:
                result.append((jp_label, elem_name, available[elem_name]))
                seen_labels.add(jp_label)

    # Also include items not in display order but in the mapping
    for item in raw_items:
        elem = item.get("element", "")
        val = item.get("value")
        if elem and isinstance(val, (int, float)):
            jp = to_japanese(elem)
            if jp and jp not in seen_labels:
                jp_label = jp
                result.append((jp_label, elem, val))
                seen_labels.add(jp_label)

    return result


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


def _build_period_label(year: str) -> str:
    """Convert a year string to a Japanese fiscal period label."""
    return f"{year}年3月期"


def _make_raw_values(
    items: list[tuple[str, str, int | float]],
    period: str,
    divisor: int,
) -> dict[str, float]:
    """Build raw_values dict for answer verification."""
    raw = {}
    for jp_label, _elem, value in items:
        raw[f"{jp_label}_{period}"] = value / divisor
    return raw


def build_pl_comparison(
    company: dict[str, str],
    filings: dict[str, Any],
) -> dict[str, Any] | None:
    """Build a 2-period income statement comparison context."""
    years = sorted(filings.keys(), reverse=True)
    if len(years) < 2:
        return None

    year_curr, year_prev = years[0], years[1]
    items_curr = _extract_items(
        filings[year_curr].get("income_statement"), PL_ELEMENTS, PL_DISPLAY_ORDER
    )
    items_prev = _extract_items(
        filings[year_prev].get("income_statement"), PL_ELEMENTS, PL_DISPLAY_ORDER
    )

    if len(items_curr) < 3:
        return None

    # Find common items
    curr_labels = {jp: (elem, val) for jp, elem, val in items_curr}
    prev_labels = {jp: (elem, val) for jp, elem, val in items_prev}
    common = [jp for jp in curr_labels if jp in prev_labels]

    if len(common) < 3:
        return None

    # Select up to 8 items
    selected = common[:8]

    # Determine scale
    all_values = [curr_labels[jp][1] for jp in selected] + [
        prev_labels[jp][1] for jp in selected
    ]
    scale_label, divisor = _choose_scale(all_values)

    # Build table
    period_curr = _build_period_label(year_curr)
    period_prev = _build_period_label(year_prev)
    headers = ["", f"{period_curr}", f"{period_prev}"]
    rows = []
    raw_values: dict[str, float] = {}

    for jp_label in selected:
        val_curr = curr_labels[jp_label][1]
        val_prev = prev_labels[jp_label][1]
        rows.append(
            [
                jp_label,
                _format_number(val_curr, divisor),
                _format_number(val_prev, divisor),
            ]
        )
        raw_values[f"{jp_label}_{year_curr}"] = val_curr / divisor
        raw_values[f"{jp_label}_{year_prev}"] = val_prev / divisor

    # Determine revenue direction for post_text
    rev_label = next((jp for jp in selected if "売上" in jp), None)
    if rev_label:
        rev_curr = curr_labels[rev_label][1]
        rev_prev = prev_labels[rev_label][1]
        direction = "増収" if rev_curr > rev_prev else "減収"
    else:
        direction = "増収"

    pre_text = _format_template(
        PRE_TEXT_TEMPLATES["pl_comparison"][0],
        company_name=company["name"],
        period=period_curr,
        gaap=company.get("gaap", ""),
    )
    post_text = _format_template(
        POST_TEXT_TEMPLATES["pl_comparison"][0],
        revenue_direction=direction,
    )

    return {
        "company_name": company["name"],
        "edinet_code": company["edinet_code"],
        "source_doc_id": filings[year_curr].get("filing", {}).get("doc_id", ""),
        "filing_year": year_curr,
        "accounting_standard": filings[year_curr].get("accounting_standard", "unknown"),
        "context_type": "pl_comparison",
        "pre_text": [pre_text],
        "post_text": [post_text],
        "table": {"headers": headers, "rows": rows},
        "raw_values": raw_values,
        "scale": scale_label,
    }


def build_bs_summary(
    company: dict[str, str],
    filings: dict[str, Any],
    year: str,
) -> dict[str, Any] | None:
    """Build a balance sheet summary context."""
    if year not in filings:
        return None

    items = _extract_items(
        filings[year].get("balance_sheet"), BS_ELEMENTS, BS_DISPLAY_ORDER
    )
    if len(items) < 4:
        return None

    selected = items[:10]
    all_values = [val for _, _, val in selected]
    scale_label, divisor = _choose_scale(all_values)

    period = _build_period_label(year)
    headers = ["", f"金額({scale_label})"]
    rows = []
    raw_values: dict[str, float] = {}

    for jp_label, _elem, value in selected:
        rows.append([jp_label, _format_number(value, divisor)])
        raw_values[f"{jp_label}_{year}"] = value / divisor

    pre_text = _format_template(
        PRE_TEXT_TEMPLATES["bs_summary"][0],
        company_name=company["name"],
        period=period,
    )
    post_text = _format_template(
        POST_TEXT_TEMPLATES["bs_summary"][0],
        asset_direction="で増加した" if len(items) > 0 else "であった",
    )

    return {
        "company_name": company["name"],
        "edinet_code": company["edinet_code"],
        "source_doc_id": filings[year].get("filing", {}).get("doc_id", ""),
        "filing_year": year,
        "accounting_standard": filings[year].get("accounting_standard", "unknown"),
        "context_type": "bs_summary",
        "pre_text": [pre_text],
        "post_text": [post_text],
        "table": {"headers": headers, "rows": rows},
        "raw_values": raw_values,
        "scale": scale_label,
    }


def build_bs_consistency(
    company: dict[str, str],
    filings: dict[str, Any],
    year: str,
) -> dict[str, Any] | None:
    """Build a BS context optimized for consistency checking questions."""
    if year not in filings:
        return None

    items = _extract_items(
        filings[year].get("balance_sheet"), BS_ELEMENTS, BS_DISPLAY_ORDER
    )
    if len(items) < 4:
        return None

    # Look for total + component pairs
    label_map = {jp: val for jp, _, val in items}
    has_total = any("合計" in jp for jp in label_map)
    if not has_total:
        return None

    selected = items[:12]
    all_values = [val for _, _, val in selected]
    scale_label, divisor = _choose_scale(all_values)

    period = _build_period_label(year)
    headers = ["", f"金額({scale_label})"]
    rows = []
    raw_values: dict[str, float] = {}

    for jp_label, _elem, value in selected:
        rows.append([jp_label, _format_number(value, divisor)])
        raw_values[f"{jp_label}_{year}"] = value / divisor

    pre_text = _format_template(
        PRE_TEXT_TEMPLATES["bs_consistency"][0],
        company_name=company["name"],
        period=period,
    )
    post_text = _format_template(
        POST_TEXT_TEMPLATES["bs_consistency"][0],
        scale=scale_label,
    )

    return {
        "company_name": company["name"],
        "edinet_code": company["edinet_code"],
        "source_doc_id": filings[year].get("filing", {}).get("doc_id", ""),
        "filing_year": year,
        "accounting_standard": filings[year].get("accounting_standard", "unknown"),
        "context_type": "bs_consistency",
        "pre_text": [pre_text],
        "post_text": [post_text],
        "table": {"headers": headers, "rows": rows},
        "raw_values": raw_values,
        "scale": scale_label,
    }


def build_cf_summary(
    company: dict[str, str],
    filings: dict[str, Any],
) -> dict[str, Any] | None:
    """Build a 2-period cash flow comparison context."""
    years = sorted(filings.keys(), reverse=True)
    year_curr = years[0]

    items_curr = _extract_items(
        filings[year_curr].get("cash_flow_statement"), CF_ELEMENTS, CF_DISPLAY_ORDER
    )
    if len(items_curr) < 3:
        return None

    # Try 2-year comparison
    if len(years) >= 2:
        year_prev = years[1]
        items_prev = _extract_items(
            filings[year_prev].get("cash_flow_statement"), CF_ELEMENTS, CF_DISPLAY_ORDER
        )
        curr_labels = {jp: (elem, val) for jp, elem, val in items_curr}
        prev_labels = {jp: (elem, val) for jp, elem, val in items_prev}
        common = [jp for jp in curr_labels if jp in prev_labels]

        if len(common) >= 3:
            selected = common[:6]
            all_values = [curr_labels[jp][1] for jp in selected] + [
                prev_labels[jp][1] for jp in selected
            ]
            scale_label, divisor = _choose_scale(all_values)

            period_curr = _build_period_label(year_curr)
            period_prev = _build_period_label(year_prev)
            headers = ["", f"{period_curr}", f"{period_prev}"]
            rows = []
            raw_values: dict[str, float] = {}

            for jp_label in selected:
                val_c = curr_labels[jp_label][1]
                val_p = prev_labels[jp_label][1]
                rows.append(
                    [
                        jp_label,
                        _format_number(val_c, divisor),
                        _format_number(val_p, divisor),
                    ]
                )
                raw_values[f"{jp_label}_{year_curr}"] = val_c / divisor
                raw_values[f"{jp_label}_{year_prev}"] = val_p / divisor

            # FCF sign
            ope_cf = curr_labels.get("営業活動によるキャッシュ・フロー")
            inv_cf = curr_labels.get("投資活動によるキャッシュ・フロー")
            if ope_cf and inv_cf:
                fcf = ope_cf[1] + inv_cf[1]
                fcf_sign = "プラス" if fcf > 0 else "マイナス"
            else:
                fcf_sign = "プラス"

            pre_text = _format_template(
                PRE_TEXT_TEMPLATES["cf_summary"][0],
                company_name=company["name"],
                period=period_curr,
            )
            post_text = _format_template(
                POST_TEXT_TEMPLATES["cf_summary"][0],
                fcf_sign=fcf_sign,
            )

            return {
                "company_name": company["name"],
                "edinet_code": company["edinet_code"],
                "source_doc_id": filings[year_curr].get("filing", {}).get("doc_id", ""),
                "filing_year": year_curr,
                "accounting_standard": filings[year_curr].get(
                    "accounting_standard", "unknown"
                ),
                "context_type": "cf_summary",
                "pre_text": [pre_text],
                "post_text": [post_text],
                "table": {"headers": headers, "rows": rows},
                "raw_values": raw_values,
                "scale": scale_label,
            }

    return None


def build_cross_statement(
    company: dict[str, str],
    filings: dict[str, Any],
    year: str,
) -> dict[str, Any] | None:
    """Build a cross-statement context combining PL and BS items."""
    if year not in filings:
        return None

    pl_items = _extract_items(
        filings[year].get("income_statement"), PL_ELEMENTS, PL_DISPLAY_ORDER
    )
    bs_items = _extract_items(
        filings[year].get("balance_sheet"), BS_ELEMENTS, BS_DISPLAY_ORDER
    )

    if len(pl_items) < 2 or len(bs_items) < 2:
        return None

    # Select key items for ratio calculations
    pl_selected = pl_items[:4]
    bs_selected = bs_items[:4]
    all_items = pl_selected + bs_selected

    all_values = [val for _, _, val in all_items]
    scale_label, divisor = _choose_scale(all_values)

    period = _build_period_label(year)
    headers = ["項目", f"金額({scale_label})"]
    rows = []
    raw_values: dict[str, float] = {}

    for jp_label, _elem, value in all_items:
        rows.append([jp_label, _format_number(value, divisor)])
        raw_values[f"{jp_label}_{year}"] = value / divisor

    pre_text = _format_template(
        PRE_TEXT_TEMPLATES["cross_statement"][0],
        company_name=company["name"],
        period=period,
        gaap=company.get("gaap", ""),
    )
    post_text = POST_TEXT_TEMPLATES["cross_statement"][0]

    return {
        "company_name": company["name"],
        "edinet_code": company["edinet_code"],
        "source_doc_id": filings[year].get("filing", {}).get("doc_id", ""),
        "filing_year": year,
        "accounting_standard": filings[year].get("accounting_standard", "unknown"),
        "context_type": "cross_statement",
        "pre_text": [pre_text],
        "post_text": [post_text],
        "table": {"headers": headers, "rows": rows},
        "raw_values": raw_values,
        "scale": scale_label,
    }


# ---------------------------------------------------------------------------
# Template helper
# ---------------------------------------------------------------------------


def _format_template(template: str, **kwargs: str) -> str:
    """Format a text template, ignoring missing keys."""
    try:
        return template.format(**kwargs)
    except KeyError:
        return template


# ---------------------------------------------------------------------------
# Main transform function
# ---------------------------------------------------------------------------


def transform_company(raw_path: Path) -> list[dict[str, Any]]:
    """Transform a single company's raw data into table contexts."""
    data = json.loads(raw_path.read_text(encoding="utf-8"))
    company = data["company"]
    filings = data.get("filings", {})

    if not filings:
        return []

    contexts: list[dict[str, Any]] = []
    years = sorted(filings.keys(), reverse=True)

    # PL comparison (2 periods)
    ctx = build_pl_comparison(company, filings)
    if ctx:
        contexts.append(ctx)

    # BS summary (latest year)
    if years:
        ctx = build_bs_summary(company, filings, years[0])
        if ctx:
            contexts.append(ctx)

    # BS consistency (latest year)
    if years:
        ctx = build_bs_consistency(company, filings, years[0])
        if ctx:
            contexts.append(ctx)

    # CF comparison
    ctx = build_cf_summary(company, filings)
    if ctx:
        contexts.append(ctx)

    # Cross-statement (latest year)
    if years:
        ctx = build_cross_statement(company, filings, years[0])
        if ctx:
            contexts.append(ctx)

    return contexts


def run(raw_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """Run Stage 2: transform all raw data into contexts."""
    raw = raw_dir or RAW_DIR
    out = output_dir or CONTEXTS_DIR
    out.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(raw.glob("*.json"))
    if not raw_files:
        logger.warning(f"No raw data files found in {raw}")
        return

    logger.info(f"Stage 2: Transforming {len(raw_files)} company files")

    total_contexts = 0
    for raw_path in raw_files:
        edinet_code = raw_path.stem
        contexts = transform_company(raw_path)

        if contexts:
            output_path = out / f"{edinet_code}_contexts.json"
            output_path.write_text(
                json.dumps(contexts, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            total_contexts += len(contexts)
            logger.info(f"  {edinet_code}: {len(contexts)} contexts")
        else:
            logger.warning(f"  {edinet_code}: no contexts generated")

    logger.info(
        f"Stage 2 complete: {total_contexts} contexts from {len(raw_files)} companies"
    )


if __name__ == "__main__":
    run()
