"""Build ``jfinqa-Lite`` — a 150-question stratified subset.

Stratification rules (from Codex review 2026-04-18):

- Primary stratum: ``subtask × accounting_standard``.
- Proportions: keep subtask ratios close to the full 1000-question split
  (≈ 83 / 30 / 37 for numerical / consistency / temporal), but give
  US-GAAP a minimum quota of 8 rows so the scarce class is still
  exercised.
- Soft constraints:
  - at most 4 questions per ``edinet_code`` (avoid single-company
    over-representation);
  - spread across industries (deferred — ``industry`` field isn't
    populated yet, so we fall back to ``edinet_code`` diversification).
- Deterministic: seeded shuffle (``seed=42``) so re-runs produce the
  same subset.

Writes ``scripts/data/final/jfinqa_lite_v1.json`` and updates
``scripts/data/final/jfinqa_lite_manifest.json`` with the row indices
relative to the full dataset.
"""

from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
FULL = ROOT / "scripts" / "data" / "final" / "jfinqa_v1.json"
OUT = ROOT / "scripts" / "data" / "final" / "jfinqa_lite_v1.json"
MANIFEST = ROOT / "scripts" / "data" / "final" / "jfinqa_lite_manifest.json"

LITE_SIZE = 150
SEED = 42
PER_COMPANY_CAP = 4

TARGET_SUBTASK = {
    "numerical_reasoning": 83,
    "consistency_checking": 30,
    "temporal_reasoning": 37,
}
# (subtask, accounting_standard) → target count
# Computed so that each subtask totals the target above, with a small
# US-GAAP floor to keep the scarce class represented.
TARGET_STRATUM: dict[tuple[str, str], int] = {
    ("numerical_reasoning", "J-GAAP"): 48,
    ("numerical_reasoning", "IFRS"): 30,
    ("numerical_reasoning", "US-GAAP"): 5,
    ("consistency_checking", "J-GAAP"): 17,
    ("consistency_checking", "IFRS"): 11,
    ("consistency_checking", "US-GAAP"): 2,
    ("temporal_reasoning", "J-GAAP"): 21,
    ("temporal_reasoning", "IFRS"): 14,
    ("temporal_reasoning", "US-GAAP"): 2,
}


def _load() -> list[dict[str, Any]]:
    with FULL.open(encoding="utf-8") as f:
        return json.load(f)


def _sample(rows: list[dict[str, Any]]) -> tuple[list[int], list[dict[str, Any]]]:
    rng = random.Random(SEED)

    # Index rows by stratum
    buckets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for idx, row in enumerate(rows):
        key = (row.get("subtask", ""), row.get("accounting_standard", ""))
        buckets[key].append(idx)

    # Shuffle within each bucket for deterministic random draw
    for indices in buckets.values():
        rng.shuffle(indices)

    picked: list[int] = []
    per_company: Counter[str] = Counter()

    def take(stratum: tuple[str, str], want: int) -> int:
        """Take up to *want* rows from *stratum* respecting company cap."""
        taken = 0
        pool = buckets.get(stratum, [])
        remaining: list[int] = []
        for idx in pool:
            if taken >= want:
                remaining.append(idx)
                continue
            code = rows[idx].get("edinet_code", "")
            if per_company[code] >= PER_COMPANY_CAP:
                remaining.append(idx)
                continue
            picked.append(idx)
            per_company[code] += 1
            taken += 1
        buckets[stratum] = remaining
        return taken

    # First pass: honor the exact targets where possible
    for stratum, target in TARGET_STRATUM.items():
        take(stratum, target)

    # Second pass: top up from any leftover rows in the same subtask to
    # reach the overall LITE_SIZE. This runs only if company caps
    # prevented some strata from hitting their target.
    if len(picked) < LITE_SIZE:
        shortfall = LITE_SIZE - len(picked)
        # Flatten remaining pools, preserving within-bucket order
        leftovers = [
            (rows[idx].get("subtask", ""), idx)
            for stratum_indices in buckets.values()
            for idx in stratum_indices
        ]
        rng.shuffle(leftovers)
        for _subtask, idx in leftovers:
            if shortfall == 0:
                break
            code = rows[idx].get("edinet_code", "")
            if per_company[code] >= PER_COMPANY_CAP:
                continue
            picked.append(idx)
            per_company[code] += 1
            shortfall -= 1

    picked.sort()
    selected = [rows[i] for i in picked]
    return picked, selected


def _distribution(selected: list[dict[str, Any]]) -> dict[str, Any]:
    subtask = Counter(r.get("subtask", "?") for r in selected)
    acc = Counter(r.get("accounting_standard", "?") for r in selected)
    companies = Counter(r.get("company_name", "?") for r in selected)
    return {
        "total": len(selected),
        "subtask": dict(subtask),
        "accounting_standard": dict(acc),
        "unique_companies": len(companies),
        "max_per_company": max(companies.values()) if companies else 0,
        "top_companies": dict(companies.most_common(10)),
    }


def main() -> int:
    rows = _load()
    picked, selected = _sample(rows)

    OUT.write_text(
        json.dumps(selected, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest = {
        "source": "scripts/data/final/jfinqa_v1.json",
        "seed": SEED,
        "lite_size": LITE_SIZE,
        "per_company_cap": PER_COMPANY_CAP,
        "target_stratum": {f"{k[0]}|{k[1]}": v for k, v in TARGET_STRATUM.items()},
        "row_indices": picked,
        "distribution": _distribution(selected),
    }
    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    dist = manifest["distribution"]
    print(f"Selected {dist['total']} rows")
    print(f"Subtask: {dist['subtask']}")
    print(f"Accounting: {dist['accounting_standard']}")
    print(f"Unique companies: {dist['unique_companies']}")
    print(f"Max per company: {dist['max_per_company']}")
    print(f"Output: {OUT.relative_to(ROOT)}")
    print(f"Manifest: {MANIFEST.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
