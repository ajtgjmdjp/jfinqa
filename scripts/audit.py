"""Audit harness for the jfinqa dataset.

Runs on ``scripts/data/final/jfinqa_v1.json`` (1000 questions) and reports:

- **DSL execution**: run each ``qa.program`` and check the result matches
  ``qa.answer`` using :func:`jfinqa._metrics.numerical_match`.
- **Duplicates**: exact duplicate and near-duplicate question texts.
- **Distribution**: company, accounting standard, subtask counts.
- **Schema sanity**: required fields present, basic types.

Writes a Markdown report to ``scripts/data/audit_report.md`` and a
machine-readable JSON to ``scripts/data/audit_report.json`` so follow-up
tooling can load the findings without re-parsing the prose.

Exit code:
  0  no audit findings
  1  findings detected (see report)
  2  cannot load dataset
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "scripts" / "data" / "final" / "jfinqa_v1.json"
REPORT_MD = ROOT / "scripts" / "data" / "audit_report.md"
REPORT_JSON = ROOT / "scripts" / "data" / "audit_report.json"

sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

from jfinqa._metrics import numerical_match  # noqa: E402
from pipeline.dsl import DSLError, execute_program  # noqa: E402

# Japanese categorical answers paired with boolean DSL results.
_TRUE_ANSWERS = frozenset(
    {
        "はい",
        "一致する",
        "True",
        "true",
        "増収",
        "増益",
        "増加",
        "上昇",
        "改善",
        "存在する",
        "上回る",
    }
)
_FALSE_ANSWERS = frozenset(
    {
        "いいえ",
        "一致しない",
        "False",
        "false",
        "減収",
        "減益",
        "減少",
        "下落",
        "悪化",
        "存在しない",
        "下回る",
    }
)


def _precision_of(gold: str) -> int | None:
    """Return the number of decimal places in the numeric part of *gold*."""
    import re

    match = re.search(r"-?[\d,]+\.(\d+)", gold)
    return len(match.group(1)) if match else 0


def _numeric_value(text: str) -> float | None:
    import re

    match = re.search(r"-?[\d,]+\.?\d*", text)
    if not match:
        return None
    try:
        return float(match.group().replace(",", ""))
    except ValueError:
        return None


def _matches_with_rounding(predicted: str, gold: str) -> bool:
    """Compare numbers allowing rounding to the gold's displayed precision.

    The canonical ``numerical_match`` uses 1% relative tolerance, which is
    too strict for small rounded answers (e.g., ROE of 0.36%). Here we
    additionally accept a prediction that, rounded to the same number of
    decimal places as the gold, equals the gold.
    """
    if numerical_match(predicted, gold, rel_tolerance=0.01):
        return True
    g = _numeric_value(gold)
    p = _numeric_value(predicted)
    if g is None or p is None:
        return False
    decimals = _precision_of(gold) or 0
    rounded = round(p, decimals)
    return abs(rounded - g) < 0.5 * 10 ** (-decimals) + 1e-9


REQUIRED_FIELDS = (
    "company_name",
    "edinet_code",
    "source_doc_id",
    "filing_year",
    "accounting_standard",
    "subtask",
    "pre_text",
    "table",
    "post_text",
    "qa",
)
REQUIRED_QA_FIELDS = ("question", "answer", "program")


@dataclass
class Findings:
    schema_missing: list[dict[str, Any]] = field(default_factory=list)
    dsl_unparsable: list[dict[str, Any]] = field(default_factory=list)
    dsl_mismatch: list[dict[str, Any]] = field(default_factory=list)
    exact_duplicates: list[dict[str, Any]] = field(default_factory=list)
    near_duplicates: list[dict[str, Any]] = field(default_factory=list)

    def total(self) -> int:
        return (
            len(self.schema_missing)
            + len(self.dsl_unparsable)
            + len(self.dsl_mismatch)
            + len(self.exact_duplicates)
            + len(self.near_duplicates)
        )


def _load() -> list[dict[str, Any]]:
    with DATA_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"Expected list, got {type(data).__name__}")
    return data


def _check_schema(idx: int, row: dict[str, Any], findings: Findings) -> bool:
    missing = [f for f in REQUIRED_FIELDS if f not in row]
    qa = row.get("qa", {})
    qa_missing = [f"qa.{f}" for f in REQUIRED_QA_FIELDS if f not in qa]
    all_missing = missing + qa_missing
    if all_missing:
        findings.schema_missing.append({"index": idx, "missing": all_missing})
        return False
    return True


def _check_dsl(idx: int, row: dict[str, Any], findings: Findings) -> None:
    qa = row["qa"]
    program = qa.get("program", [])
    gold = str(qa.get("answer", ""))

    if not program:
        findings.dsl_unparsable.append(
            {"index": idx, "id": row.get("id"), "reason": "empty program"}
        )
        return

    try:
        result = execute_program(program)
    except DSLError as exc:
        findings.dsl_unparsable.append(
            {
                "index": idx,
                "id": row.get("id"),
                "reason": str(exc),
                "program": program,
            }
        )
        return
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        findings.dsl_unparsable.append(
            {
                "index": idx,
                "id": row.get("id"),
                "reason": f"{type(exc).__name__}: {exc}",
                "program": program,
            }
        )
        return

    predicted = str(result)
    question = qa.get("question", "")

    if isinstance(result, bool):
        expected = _TRUE_ANSWERS if result else _FALSE_ANSWERS
        if gold not in expected:
            findings.dsl_mismatch.append(
                {
                    "index": idx,
                    "id": row.get("id"),
                    "gold": gold,
                    "dsl_result": predicted,
                    "question": question,
                }
            )
        return

    # Numeric: gold may carry units like "%" or "百万円". We accept
    # either the 1% relative tolerance or a match after rounding to the
    # displayed precision of the gold answer.
    if not _matches_with_rounding(predicted, gold):
        findings.dsl_mismatch.append(
            {
                "index": idx,
                "id": row.get("id"),
                "gold": gold,
                "dsl_result": predicted,
                "question": question,
            }
        )


def _check_duplicates(rows: list[dict[str, Any]], findings: Findings) -> None:
    from difflib import SequenceMatcher

    seen: dict[str, int] = {}
    for idx, row in enumerate(rows):
        q = row.get("qa", {}).get("question", "").strip()
        if not q:
            continue
        if q in seen:
            findings.exact_duplicates.append(
                {
                    "first_index": seen[q],
                    "duplicate_index": idx,
                    "question": q,
                }
            )
        else:
            seen[q] = idx

    # Near-duplicate: same (company, subtask, filing_year) with question
    # similarity >= 0.90. Grouping by filing_year avoids quadratic blow-up
    # and keeps the audit runnable on the full dataset.
    groups: dict[tuple[str, str, str], list[int]] = {}
    for idx, row in enumerate(rows):
        q = row.get("qa", {}).get("question", "").strip()
        if not q:
            continue
        key = (
            row.get("company_name", ""),
            row.get("subtask", ""),
            row.get("filing_year", ""),
        )
        groups.setdefault(key, []).append(idx)

    for _key, indices in groups.items():
        if len(indices) < 2:
            continue
        for i, a in enumerate(indices):
            qa_a = rows[a].get("qa", {})
            for b in indices[i + 1 :]:
                qa_b = rows[b].get("qa", {})
                q_a = qa_a.get("question", "")
                q_b = qa_b.get("question", "")
                # Two questions that differ in a few characters but have
                # different gold answers are asking about different
                # metrics, not duplicates. Only flag pairs whose answers
                # also match after trivial normalization.
                if qa_a.get("answer", "").strip() != qa_b.get("answer", "").strip():
                    continue
                ratio = SequenceMatcher(a=q_a, b=q_b, autojunk=False).ratio()
                if ratio >= 0.90 and q_a != q_b:
                    findings.near_duplicates.append(
                        {
                            "first_index": a,
                            "similar_index": b,
                            "ratio": round(ratio, 3),
                            "question_a": q_a,
                            "question_b": q_b,
                            "answer": qa_a.get("answer"),
                        }
                    )


def _distribution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total": len(rows),
        "subtask": dict(Counter(r.get("subtask", "?") for r in rows)),
        "accounting_standard": dict(
            Counter(r.get("accounting_standard", "?") for r in rows)
        ),
        "filing_year": dict(Counter(r.get("filing_year", "?") for r in rows)),
        "unique_companies": len({r.get("edinet_code", "?") for r in rows}),
        "top_companies": dict(
            Counter(r.get("company_name", "?") for r in rows).most_common(15)
        ),
    }


def _render(findings: Findings, dist: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# jfinqa audit report")
    lines.append("")
    lines.append(f"Source: `{DATA_FILE.relative_to(ROOT)}`")
    lines.append(f"Total questions: {dist['total']}")
    lines.append(f"Unique companies (EDINET code): {dist['unique_companies']}")
    lines.append("")
    lines.append("## Distribution")
    lines.append("")
    lines.append("### Subtask")
    for k, v in sorted(dist["subtask"].items()):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("### Accounting standard")
    for k, v in sorted(dist["accounting_standard"].items()):
        pct = 100 * v / dist["total"]
        lines.append(f"- `{k}`: {v} ({pct:.1f}%)")
    lines.append("")
    lines.append("### Filing year")
    for k, v in sorted(dist["filing_year"].items()):
        lines.append(f"- `{k}`: {v}")
    lines.append("")
    lines.append("### Top 15 companies")
    for k, v in dist["top_companies"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")

    lines.append("## Findings")
    lines.append("")
    lines.append(f"- schema missing fields: {len(findings.schema_missing)}")
    lines.append(f"- DSL unparsable / execution error: {len(findings.dsl_unparsable)}")
    lines.append(f"- DSL result ↔ answer mismatch: {len(findings.dsl_mismatch)}")
    lines.append(f"- exact duplicate questions: {len(findings.exact_duplicates)}")
    lines.append(f"- near-duplicate questions: {len(findings.near_duplicates)}")
    lines.append("")

    for heading, entries in [
        ("Schema missing (first 20)", findings.schema_missing[:20]),
        ("DSL unparsable (first 20)", findings.dsl_unparsable[:20]),
        ("DSL mismatch (first 20)", findings.dsl_mismatch[:20]),
        ("Exact duplicates (first 20)", findings.exact_duplicates[:20]),
        ("Near duplicates (first 20)", findings.near_duplicates[:20]),
    ]:
        if not entries:
            continue
        lines.append(f"### {heading}")
        lines.append("")
        lines.append("```json")
        lines.append(json.dumps(entries, ensure_ascii=False, indent=2))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    try:
        rows = _load()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR loading dataset: {exc}", file=sys.stderr)
        return 2

    findings = Findings()
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            findings.schema_missing.append({"index": idx, "reason": "not a dict"})
            continue
        if _check_schema(idx, row, findings):
            _check_dsl(idx, row, findings)
    _check_duplicates(rows, findings)

    dist = _distribution(rows)

    report_md = _render(findings, dist)
    REPORT_MD.write_text(report_md, encoding="utf-8")

    payload = {
        "total": dist["total"],
        "distribution": dist,
        "findings_count": {
            "schema_missing": len(findings.schema_missing),
            "dsl_unparsable": len(findings.dsl_unparsable),
            "dsl_mismatch": len(findings.dsl_mismatch),
            "exact_duplicates": len(findings.exact_duplicates),
            "near_duplicates": len(findings.near_duplicates),
        },
        "findings": {
            "schema_missing": findings.schema_missing,
            "dsl_unparsable": findings.dsl_unparsable,
            "dsl_mismatch": findings.dsl_mismatch,
            "exact_duplicates": findings.exact_duplicates,
            "near_duplicates": findings.near_duplicates,
        },
    }
    REPORT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Audited {dist['total']} rows.")
    print(f"Findings total: {findings.total()}")
    print(f"  schema_missing: {len(findings.schema_missing)}")
    print(f"  dsl_unparsable: {len(findings.dsl_unparsable)}")
    print(f"  dsl_mismatch: {len(findings.dsl_mismatch)}")
    print(f"  exact_duplicates: {len(findings.exact_duplicates)}")
    print(f"  near_duplicates: {len(findings.near_duplicates)}")
    print(f"Report: {REPORT_MD.relative_to(ROOT)}")
    print(f"JSON:   {REPORT_JSON.relative_to(ROOT)}")

    return 1 if findings.total() > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
