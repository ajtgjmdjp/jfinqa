"""Stage 1: Collect financial data from EDINET.

Fetches structured financial statements (BS, PL, CF) for each company
in the pool across target years. Results are cached as JSON files.

Searches narrow filing windows (June-Aug for March FY, Mar-Apr for Dec FY)
to avoid iterating all 365 days per year.

Usage::

    python -m scripts.pipeline.s1_collect
    # or via run_pipeline.py --stage 1
"""

from __future__ import annotations

import datetime
import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from loguru import logger

from scripts.pipeline.config import COMPANY_POOL, RAW_DIR, TARGET_YEARS

# Filing windows: most Japanese companies file annual reports in these months.
# March FY end (majority): file in June-July
# December FY end: file in March-April
_FILING_WINDOWS = [
    (6, 1, 8, 31),  # June-August (March FY end)
    (3, 1, 5, 31),  # March-May (December FY end)
]


def _serialize_statement(stmt_data: Any) -> list[dict[str, Any]] | None:
    """Convert a StatementData to a serializable list, or None if empty."""
    if not stmt_data:
        return None
    result: list[dict[str, Any]] = stmt_data.to_dicts()
    return result


def _find_annual_report(
    client: Any,
    edinet_code: str,
    year: str,
) -> Any | None:
    """Search narrow filing windows to find an annual report.

    Returns the FinancialStatement or None if not found.
    """
    yr = int(year)

    for m_start, d_start, m_end, d_end in _FILING_WINDOWS:
        start = datetime.date(yr, m_start, d_start)
        end = datetime.date(yr, m_end, d_end)

        try:
            filings = client.get_filings(
                start_date=start,
                end_date=end,
                edinet_code=edinet_code,
                doc_type="annual_report",
            )
        except Exception as e:
            logger.debug(f"    Window {start}~{end}: {e}")
            continue

        if filings:
            # Use most recent filing with XBRL
            xbrl_filings = [f for f in filings if f.has_xbrl]
            if not xbrl_filings:
                continue

            filing = sorted(
                xbrl_filings, key=lambda f: f.filing_date, reverse=True
            )[0]
            logger.info(
                f"  {edinet_code}/{year}: "
                f"Found {filing.doc_id} ({filing.description})"
            )

            # Download and parse
            zip_path = client.download_document(
                filing.doc_id, format="xbrl"
            )
            return client._parse_filing(filing, zip_path)

    return None


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
            stmt = _find_annual_report(client, edinet_code, year)
            if stmt is None:
                logger.warning(f"  {edinet_code}/{year}: no filing found")
                continue

            filings[year] = {
                "filing": stmt.filing.model_dump(mode="json"),
                "accounting_standard": stmt.accounting_standard.value,
                "balance_sheet": _serialize_statement(stmt.balance_sheet),
                "income_statement": _serialize_statement(
                    stmt.income_statement
                ),
                "cash_flow_statement": _serialize_statement(
                    stmt.cash_flow_statement
                ),
                "summary": _serialize_statement(stmt.summary),
            }
            logger.info(
                f"  {edinet_code}/{year}: "
                f"BS={bool(stmt.balance_sheet)} "
                f"PL={bool(stmt.income_statement)} "
                f"CF={bool(stmt.cash_flow_statement)}"
            )
        except Exception as e:
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

    logger.info(
        f"Stage 1: Collecting data for {len(COMPANY_POOL)} companies"
    )
    logger.info(f"Target years: {TARGET_YEARS}")
    logger.info(f"Output: {out}")

    collected = 0
    skipped = 0
    errors = 0

    # Use higher rate limit for batch collection
    with EdinetClient(rate_limit=2.0) as client:
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
        f"Stage 1 complete: "
        f"{collected} collected, {skipped} skipped, {errors} errors"
    )


if __name__ == "__main__":
    run()
