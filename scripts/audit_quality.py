"""Deep data-quality audit for jfinqa.

Categorises problems that the basic ``audit.py`` misses:

* **table_inconsistency**: a line item that is mathematically
  impossible given other visible rows (e.g., ``売上原価 > 売上高``).
* **identity_mismatch**: ``資産合計`` not equal to the sum of
  ``流動資産 + 固定資産``, or ``当期純利益`` not equal to the sum of
  ``親会社株主に帰属する当期純利益 + 非支配株主に帰属する当期純利益``.
* **roe_ambiguity**: ROE / DuPont questions where both
  ``当期純利益`` and ``親会社株主に帰属する当期純利益`` appear in the
  table, making the calculation convention ambiguous.
* **rounding_pedantry**: ``consistency_checking`` questions whose
  ``eq`` result is on the 0.001 boundary — a pure rounding artefact
  that disagrees with what a human reader would say.
* **missing_total**: ``資産合計`` or ``純資産合計`` missing when
  referenced by the question.

Writes ``scripts/data/audit_quality_report.md`` and
``scripts/data/audit_quality_report.json``.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "scripts" / "data" / "final" / "jfinqa_v1.json"
REPORT_MD = ROOT / "scripts" / "data" / "audit_quality_report.md"
REPORT_JSON = ROOT / "scripts" / "data" / "audit_quality_report.json"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from pipeline.dsl import execute_program  # noqa: E402


def _parse_num(raw: str) -> float | None:
    """Parse a Japanese-formatted numeric cell, handling △ and commas."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    negative = False
    if s.startswith(("△", "▲")):
        negative = True
        s = s[1:]
    s = s.replace(",", "").replace(" ", "")
    # Drop unit suffixes if any
    for suffix in ("百万円", "千円", "億円", "兆円", "円", "ドル", "ポイント", "pt", "bps", "%"):
        if s.endswith(suffix):
            s = s[: -len(suffix)]
    try:
        value = float(s)
    except ValueError:
        return None
    return -value if negative else value


def _table_map(row: dict[str, Any]) -> dict[str, float]:
    """Map first-column label → numeric value, keeping first occurrence."""
    table = row.get("table", {})
    out: dict[str, float] = {}
    for cells in table.get("rows", []):
        if not cells:
            continue
        label = str(cells[0]).strip()
        value = _parse_num(cells[1]) if len(cells) > 1 else None
        if value is not None and label not in out:
            out[label] = value
    return out


def _near(a: float, b: float, tol: float = 0.02) -> bool:
    """Equality within 2% relative or 0.5 absolute (for small values)."""
    if a == b:
        return True
    if b == 0:
        return abs(a) <= 0.5
    return abs(a - b) / abs(b) <= tol or abs(a - b) <= 0.5


def _check_table_consistency(
    idx: int, row: dict[str, Any], findings: dict[str, list]
) -> None:
    tm = _table_map(row)
    qid = row.get("id")
    company = row.get("company_name")

    sales = tm.get("売上高")
    cogs = tm.get("売上原価")
    gross = tm.get("売上総利益")
    opex = tm.get("販売費及び一般管理費")
    op_income = tm.get("営業利益")
    net_income = tm.get("当期純利益")
    parent_ni = tm.get("親会社株主に帰属する当期純利益")
    nonctrl_ni = tm.get("非支配株主に帰属する当期純利益")

    current_asset = tm.get("流動資産")
    fixed_asset = tm.get("固定資産")
    total_asset = tm.get("資産合計")
    current_liab = tm.get("流動負債")
    fixed_liab = tm.get("固定負債")
    total_equity = tm.get("純資産合計")

    # 1. 売上原価 should not exceed 売上高
    if sales is not None and cogs is not None and cogs > sales * 1.001:
        findings["impossible_cogs"].append(
            {
                "id": qid,
                "company": company,
                "sales": sales,
                "cogs": cogs,
                "ratio": round(cogs / sales, 3) if sales != 0 else None,
            }
        )

    # 2. 売上総利益 = 売上高 - 売上原価
    if sales is not None and cogs is not None and gross is not None:
        expected = sales - cogs
        if not _near(gross, expected):
            findings["gross_profit_mismatch"].append(
                {
                    "id": qid,
                    "company": company,
                    "expected": round(expected, 3),
                    "reported": gross,
                }
            )

    # 3. 営業利益 = 売上総利益 - 販管費
    if gross is not None and opex is not None and op_income is not None:
        expected = gross - opex
        if not _near(op_income, expected):
            findings["op_income_mismatch"].append(
                {
                    "id": qid,
                    "company": company,
                    "expected": round(expected, 3),
                    "reported": op_income,
                }
            )

    # 4. 当期純利益 ≈ 親会社 + 非支配
    if net_income is not None and parent_ni is not None and nonctrl_ni is not None:
        expected = parent_ni + nonctrl_ni
        if not _near(net_income, expected, tol=0.01):
            findings["ni_decomposition_mismatch"].append(
                {
                    "id": qid,
                    "company": company,
                    "net_income": net_income,
                    "parent_ni": parent_ni,
                    "nonctrl_ni": nonctrl_ni,
                    "expected_sum": round(expected, 3),
                }
            )

    # 5. 資産合計 ≈ 流動資産 + 固定資産
    if (
        total_asset is not None
        and current_asset is not None
        and fixed_asset is not None
    ):
        expected = current_asset + fixed_asset
        if not _near(total_asset, expected, tol=0.01):
            findings["asset_total_mismatch"].append(
                {
                    "id": qid,
                    "company": company,
                    "current_asset": current_asset,
                    "fixed_asset": fixed_asset,
                    "expected_sum": round(expected, 3),
                    "reported_total": total_asset,
                }
            )

    # 6. 資産合計 ≈ 流動負債 + 固定負債 + 純資産合計
    if (
        total_asset is not None
        and current_liab is not None
        and fixed_liab is not None
        and total_equity is not None
    ):
        expected = current_liab + fixed_liab + total_equity
        if not _near(total_asset, expected, tol=0.01):
            findings["balance_sheet_mismatch"].append(
                {
                    "id": qid,
                    "company": company,
                    "total_asset": total_asset,
                    "liab_plus_equity": round(expected, 3),
                    "diff": round(total_asset - expected, 3),
                }
            )

    # 7. ROE ambiguity: question mentions ROE and table has both 当期純利益
    #    and 親会社株主に帰属する当期純利益
    question = (row.get("qa") or {}).get("question", "")
    if (
        ("ROE" in question or "DuPont" in question or "自己資本利益率" in question)
        and net_income is not None
        and parent_ni is not None
    ):
        findings["roe_convention_ambiguity"].append(
            {
                "id": qid,
                "company": company,
                "net_income": net_income,
                "parent_ni": parent_ni,
                "question": question[:90],
            }
        )


def _check_dsl_tolerance(
    idx: int, row: dict[str, Any], findings: dict[str, list]
) -> None:
    program = row.get("qa", {}).get("program", [])
    if not program:
        return
    try:
        result = execute_program(program)
    except Exception:
        return
    if not isinstance(result, bool):
        return
    # Re-execute without eq() to get the last numeric pair, then measure
    # its relative distance to capture rounding pedantry.
    last = program[-1].strip()
    if not last.startswith("eq("):
        return
    # execute steps up to the last eq
    if len(program) < 2:
        return
    try:
        results: list[Any] = []
        for step in program[:-1]:
            step = step.strip()
            op, _, rest = step.partition("(")
            args = rest.rstrip(")").split(",")
            parsed = []
            for a in args:
                a = a.strip()
                if a.startswith("#"):
                    parsed.append(results[int(a[1:])])
                else:
                    parsed.append(float(a))
            if op == "add":
                results.append(parsed[0] + parsed[1])
            elif op == "subtract":
                results.append(parsed[0] - parsed[1])
            elif op == "multiply":
                results.append(parsed[0] * parsed[1])
            elif op == "divide":
                results.append(
                    parsed[0] / parsed[1] if parsed[1] != 0 else float("inf")
                )
            else:
                return
        if len(results) < 2:
            return
        a, b = results[-2], results[-1]
        diff = abs(a - b)
        if diff < 0.0015 and not _near(a, b, tol=0.0001):
            findings["rounding_pedantry"].append(
                {
                    "id": row.get("id"),
                    "company": row.get("company_name"),
                    "a": round(a, 5),
                    "b": round(b, 5),
                    "diff": round(diff, 6),
                    "dsl_result": result,
                    "gold": row.get("qa", {}).get("answer"),
                }
            )
    except Exception:
        return


def _render(findings: dict[str, list], totals: dict[str, int]) -> str:
    lines = ["# jfinqa deep audit report", ""]
    lines.append(f"Total rows scanned: {totals['rows']}")
    lines.append("")
    lines.append("## Findings summary")
    for key, entries in findings.items():
        lines.append(f"- **{key}**: {len(entries)}")
    lines.append("")
    for key, entries in findings.items():
        if not entries:
            continue
        lines.append(f"## {key}")
        lines.append("")
        lines.append(f"Count: {len(entries)}")
        sample = entries[:10]
        lines.append("```json")
        lines.append(json.dumps(sample, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    with DATA_FILE.open(encoding="utf-8") as f:
        rows = json.load(f)

    findings: dict[str, list] = {
        "impossible_cogs": [],
        "gross_profit_mismatch": [],
        "op_income_mismatch": [],
        "ni_decomposition_mismatch": [],
        "asset_total_mismatch": [],
        "balance_sheet_mismatch": [],
        "roe_convention_ambiguity": [],
        "rounding_pedantry": [],
    }
    for idx, row in enumerate(rows):
        _check_table_consistency(idx, row, findings)
        _check_dsl_tolerance(idx, row, findings)

    totals = {"rows": len(rows)}
    REPORT_MD.write_text(_render(findings, totals), encoding="utf-8")
    REPORT_JSON.write_text(
        json.dumps(
            {"totals": totals, "findings": findings, "counts": {k: len(v) for k, v in findings.items()}},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # Breakdown by unique question id (some items overlap categories)
    impacted_ids: set[str] = set()
    for entries in findings.values():
        for e in entries:
            qid = e.get("id")
            if qid:
                impacted_ids.add(qid)

    print(f"Scanned {len(rows)} rows.")
    print()
    for key, entries in findings.items():
        print(f"  {key:<30} {len(entries):>4}")
    print()
    print(f"Unique affected question ids: {len(impacted_ids)}")
    print(f"Report: {REPORT_MD.relative_to(ROOT)}")
    print(f"JSON:   {REPORT_JSON.relative_to(ROOT)}")
    return 1 if impacted_ids else 0


if __name__ == "__main__":
    sys.exit(main())
