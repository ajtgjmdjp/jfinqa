"""Post-collection integrity check for scripts/data_*/raw/.

Verifies every raw JSON produced by stage 1:

* Filename EDINET code matches ``top.edinet_code`` and
  ``filings[*].filing.edinet_code``.
* ``filings[*].filing.doc_type`` equals ``"120"`` (annual report).
* ``filings[*].filing.company_name`` is present.
* ``filings[*].filing.edinet_code`` == filename stem.

Exit code:
  0  all files consistent
  1  one or more violations found
  2  cannot read data directory
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_raw_integrity.py <raw_dir>", file=sys.stderr)
        return 2

    raw_dir = Path(sys.argv[1])
    if not raw_dir.exists() or not raw_dir.is_dir():
        print(f"ERROR: {raw_dir} not found", file=sys.stderr)
        return 2

    violations: list[dict] = []
    total = 0
    for path in sorted(raw_dir.glob("E*.json")):
        total += 1
        expected_code = path.stem
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            violations.append({"file": path.name, "issue": "unreadable", "detail": str(exc)})
            continue

        company = data.get("company", {})
        company_code = company.get("edinet_code")
        if company_code != expected_code:
            violations.append(
                {
                    "file": path.name,
                    "issue": "company_code_mismatch",
                    "expected": expected_code,
                    "found": company_code,
                }
            )

        filings = data.get("filings") or {}
        for year, filing_record in filings.items():
            filing = (filing_record or {}).get("filing", {}) or {}
            fc = filing.get("edinet_code")
            if fc != expected_code:
                violations.append(
                    {
                        "file": path.name,
                        "year": year,
                        "issue": "filing_code_mismatch",
                        "expected": expected_code,
                        "found": fc,
                    }
                )
            dt = filing.get("doc_type")
            if dt and dt != "120":
                violations.append(
                    {
                        "file": path.name,
                        "year": year,
                        "issue": "non_annual_doc_type",
                        "doc_type": dt,
                    }
                )
            if not filing.get("company_name"):
                violations.append(
                    {
                        "file": path.name,
                        "year": year,
                        "issue": "missing_company_name",
                    }
                )

    print(f"Scanned {total} raw files.")
    print(f"Violations: {len(violations)}")
    for v in violations[:30]:
        print(" ", v)
    if len(violations) > 30:
        print(f"  ... {len(violations) - 30} more")
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
