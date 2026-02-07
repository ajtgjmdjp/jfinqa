"""Stage 1: Collect financial data from EDINET.

Fetches structured financial statements (BS, PL, CF) for each company
in the pool across target years. Results are cached as JSON files.

Usage::

    python -m scripts.pipeline.s1_collect
    # or via run_pipeline.py --stage 1
"""

from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from loguru import logger

from scripts.pipeline.config import COMPANY_POOL, RAW_DIR, TARGET_YEARS


def _serialize_statement(stmt_data: Any) -> list[dict[str, Any]] | None:
    """Convert a StatementData to a serializable list, or None if empty."""
    if not stmt_data:
        return None
    result: list[dict[str, Any]] = stmt_data.to_dicts()
    return result


def collect_company(
    client: Any,
    company: dict[str, str],
    output_dir: Path,
) -> bool:
    """Collect financial data for a single company.

    Returns True if new data was collected, False if skipped (cached).
    """
    edinet_code = company["edinet_code"]
    output_path = output_dir / f"{edinet_code}.json"

    if output_path.exists():
        logger.debug(f"Skipping {edinet_code} (cached)")
        return False

    filings: dict[str, Any] = {}

    for year in TARGET_YEARS:
        try:
            stmt = client.get_financial_statements(
                edinet_code,
                period=year,
                doc_type="annual_report",
            )
            filings[year] = {
                "filing": stmt.filing.model_dump(mode="json"),
                "accounting_standard": stmt.accounting_standard.value,
                "balance_sheet": _serialize_statement(stmt.balance_sheet),
                "income_statement": _serialize_statement(stmt.income_statement),
                "cash_flow_statement": _serialize_statement(stmt.cash_flow_statement),
                "summary": _serialize_statement(stmt.summary),
            }
            logger.info(
                f"  {edinet_code}/{year}: BS={bool(stmt.balance_sheet)} "
                f"PL={bool(stmt.income_statement)} CF={bool(stmt.cash_flow_statement)}"
            )
        except (ValueError, Exception) as e:
            logger.warning(f"  {edinet_code}/{year}: {e}")

    if not filings:
        logger.warning(f"No data for {edinet_code}, skipping")
        return False

    result = {
        "company": company,
        "filings": filings,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info(f"Saved {edinet_code} ({len(filings)} year(s))")
    return True


def run(output_dir: Path | None = None) -> None:
    """Run Stage 1: collect data for all companies in the pool."""
    try:
        from edinet_mcp import EdinetClient
    except ImportError:
        logger.error(
            "edinet-mcp is not installed. Install it with:\n"
            "  pip install -e /Users/rei/Project/edinet-mcp"
        )
        sys.exit(1)

    out = output_dir or RAW_DIR
    out.mkdir(parents=True, exist_ok=True)

    logger.info(f"Stage 1: Collecting data for {len(COMPANY_POOL)} companies")
    logger.info(f"Target years: {TARGET_YEARS}")
    logger.info(f"Output: {out}")

    collected = 0
    skipped = 0
    errors = 0

    with EdinetClient() as client:
        for i, company in enumerate(COMPANY_POOL, 1):
            name = company["name"]
            code = company["edinet_code"]
            logger.info(f"[{i}/{len(COMPANY_POOL)}] {name} ({code})")
            try:
                if collect_company(client, company, out):
                    collected += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"  Failed: {e}")
                errors += 1

    logger.info(
        f"Stage 1 complete: {collected} collected, {skipped} skipped, {errors} errors"
    )


if __name__ == "__main__":
    run()
