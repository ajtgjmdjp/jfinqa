"""Detect the actual accounting standard (IFRS / J-GAAP / US-GAAP) for each
company in ``scripts/data/raw/`` by inspecting the XBRL element namespaces
and element-name suffixes.

Rationale
---------
The field ``filings[<year>].accounting_standard`` stored in the raw JSON is
unreliable — in this dataset it is hard-coded to ``"J-GAAP"`` for every
company regardless of the actual filing. Likewise ``COMPANY_POOL[*].gaap``
in ``scripts/pipeline/config.py`` was authored by hand and diverges from the
real taxonomy used by the filer. Downstream stages (s2_transform, stats,
stratification) consume ``company.gaap``, so a mismatch corrupts metadata
and pre_text ("J-GAAP適用" while the table uses IFRS labels).

Detection rules (applied in order, first match wins)
----------------------------------------------------
For each company, take the **latest year's** filing, then restrict to
elements whose ``context`` starts with ``CurrentYear`` (i.e. the primary
reporting period — excludes ``Prior4Year`` / ``Prior3Year`` historical
comparison data in ``SummaryOfBusinessResults``).

1. **US-GAAP** — ``USGAAP``-suffixed element outside
   ``SummaryOfBusinessResults`` (typically
   ``ConsolidatedStatementOf{Income,Equity,CashFlows,ComprehensiveIncome}USGAAPTextBlock``)
   appears >= 3 times. This is the unambiguous marker for a US-GAAP filer.
2. **IFRS** — The dedicated IFRS taxonomy namespace ``jpigp_cor`` is used by
   >= 10 current-year elements. ``jpigp_cor`` is the EDINET namespace that
   only IFRS filers populate. (Backup signal: the company also emits many
   ``...IFRS`` element suffixes, e.g.
   ``ProfitLossBeforeTaxIFRS``.)
3. **J-GAAP** — otherwise. The J-GAAP (``jppfs_cor``) statement namespace is
   the legacy default.

Usage
-----
    python scripts/detect_accounting_standard.py          # print table
    python scripts/detect_accounting_standard.py --json   # emit JSON map
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Literal

RAW_DIR = Path(__file__).resolve().parent / "data" / "raw"

GAAP = Literal["IFRS", "J-GAAP", "US-GAAP"]


def _latest_year(filings: dict[str, dict]) -> str:
    # Year keys are strings; pick the lexicographically largest.
    return max(filings.keys())


def _signals(yd: dict) -> dict[str, int]:
    """Return counts of detection signals for a single filing year."""
    ns = Counter()
    ifrs_pure = 0   # IFRS-suffixed elements outside SummaryOfBusinessResults
    ifrs_any = 0    # IFRS-suffixed anywhere (includes historical summary)
    usgaap_pure = 0  # USGAAP-suffixed outside SummaryOfBusinessResults
    usgaap_any = 0
    total_cy = 0

    for stmt_name in ("balance_sheet", "income_statement", "cash_flow_statement"):
        items = yd.get(stmt_name) or []
        for it in items:
            ctx = it.get("context", "")
            if not ctx.startswith("CurrentYear"):
                continue
            total_cy += 1
            el = it.get("element", "")
            nsp = it.get("namespace", "")
            for tag in ("jpigp_cor", "jppfs_cor", "jpcrp_cor", "jpusg_cor"):
                if tag in nsp:
                    ns[tag] += 1
                    break
            in_summary = "SummaryOfBusinessResults" in el
            if "IFRS" in el:
                ifrs_any += 1
                if not in_summary:
                    ifrs_pure += 1
            if "USGAAP" in el:
                usgaap_any += 1
                if not in_summary:
                    usgaap_pure += 1

    return {
        "ns_jpigp": ns.get("jpigp_cor", 0),
        "ns_jppfs": ns.get("jppfs_cor", 0),
        "ns_jpcrp": ns.get("jpcrp_cor", 0),
        "ns_jpusg": ns.get("jpusg_cor", 0),
        "ifrs_pure": ifrs_pure,
        "ifrs_any": ifrs_any,
        "usgaap_pure": usgaap_pure,
        "usgaap_any": usgaap_any,
        "total_cy": total_cy,
    }


def classify(sig: dict[str, int]) -> GAAP:
    # Rule 1: US-GAAP
    if sig["usgaap_pure"] >= 3 or sig["ns_jpusg"] >= 10:
        return "US-GAAP"
    # Rule 2: IFRS
    if sig["ns_jpigp"] >= 10:
        return "IFRS"
    # Fallback: J-GAAP
    return "J-GAAP"


def detect_for_file(path: Path) -> dict:
    d = json.loads(path.read_text())
    filings = d.get("filings", {})
    company = d.get("company", {})
    if not filings:
        return {
            "edinet_code": company.get("edinet_code", path.stem),
            "cfg_name": company.get("name"),
            "cfg_gaap": company.get("gaap"),
            "detected": None,
            "signals": None,
            "actual_name": None,
        }
    year = _latest_year(filings)
    yd = filings[year]
    fi = yd.get("filing") or {}
    sig = _signals(yd)
    detected = classify(sig)
    return {
        "edinet_code": company.get("edinet_code", path.stem),
        "cfg_name": company.get("name"),
        "cfg_gaap": company.get("gaap"),
        "detected": detected,
        "signals": sig,
        "actual_name": fi.get("company_name"),
        "year": year,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="Emit a JSON map")
    ap.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Directory containing <EDINET>.json files",
    )
    args = ap.parse_args()

    rows = []
    for path in sorted(args.raw_dir.glob("E*.json")):
        rows.append(detect_for_file(path))

    if args.json:
        payload = {
            r["edinet_code"]: {
                "detected": r["detected"],
                "cfg_gaap": r["cfg_gaap"],
                "cfg_name": r["cfg_name"],
                "actual_name": r["actual_name"],
                "signals": r["signals"],
            }
            for r in rows
        }
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    # Pretty print
    totals = Counter()
    mism_rows = []
    print(
        f"{'code':<8} {'cfg_gaap':<8} {'detected':<8} "
        f"{'jpigp':>5} {'jppfs':>5} {'ifrs_p':>6} {'usg_p':>5}  "
        f"cfg_name -> actual_name"
    )
    print("-" * 120)
    for r in rows:
        det = r["detected"] or "?"
        sig = r["signals"] or {}
        mismatch = r["cfg_gaap"] != det
        flag = "!" if mismatch else " "
        print(
            f"{r['edinet_code']:<8} "
            f"{r['cfg_gaap']!s:<8} {det:<8} "
            f"{sig.get('ns_jpigp', 0):>5} "
            f"{sig.get('ns_jppfs', 0):>5} "
            f"{sig.get('ifrs_pure', 0):>6} "
            f"{sig.get('usgaap_pure', 0):>5} "
            f"{flag} {r['cfg_name']} -> {r['actual_name']}"
        )
        totals[det] += 1
        if mismatch:
            mism_rows.append(r)

    print("-" * 120)
    print(f"Totals: {dict(totals)}")
    print(f"Mismatches: {len(mism_rows)} / {len(rows)}")
    if mism_rows:
        print("\nMismatch detail (cfg -> detected):")
        by_transition = Counter()
        for r in mism_rows:
            by_transition[(r["cfg_gaap"], r["detected"])] += 1
            print(
                f"  {r['edinet_code']}  {r['cfg_gaap']} -> {r['detected']}  "
                f"[{r['cfg_name']}]"
            )
        print(f"\nTransition counts: {dict(by_transition)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
