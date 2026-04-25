"""Adversarial baselines for jfinqa (Codex Q10 MVP).

Implements two non-LLM controls that bracket the benchmark's non-triviality:

1. ``answer_prior`` (subtask-level majority/most-common answer):
   Predicts every item with the global mode of its subtask's gold answer set.
   For ``numerical_reasoning``, percentage answers are bucketed to one decimal
   place to avoid pathological splitting; ``consistency_checking`` and
   ``temporal_reasoning`` use verbatim mode counts.

2. ``table_shuffle`` (evidence-corruption): **stubbed**, owned by
   ``hypothesis-reasoning``. Replaces an item's table with a uniformly-sampled
   peer item from the same subtask, then asks the same model to answer.
   Drops in accuracy quantify how much the benchmark depends on the actual
   table contents.

Reference: Codex Turn 4 priority ``table-shuffle > answer-prior > regex``,
with the framing guardrail that table-shuffle is the **primary** evidence
of evidence-dependence and reasoning regimes are a secondary observation.

Usage::

    python -m scripts.adversarial_baselines \\
        --baseline answer_prior \\
        --data scripts/data/final/jfinqa_v1.json \\
        --output scripts/data/baselines_full_1000/answer_prior__metrics.json
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_questions(path: Path) -> list[dict[str, Any]]:
    """Load the jfinqa final dataset (list-of-records JSON)."""
    return json.loads(path.read_text())


def _bucket_numeric(answer: str) -> str:
    """Bucket numeric answers to 1 decimal place to avoid mode degeneracy.

    For example, ``5.43%`` and ``5.44%`` both bucket to ``5.4%``.
    Non-numeric answers pass through verbatim.
    """
    raw = answer.strip()
    is_pct = raw.endswith("%")
    cleaned = raw.rstrip("%").replace(",", "").strip()
    try:
        val = float(cleaned)
    except ValueError:
        return raw
    bucketed = f"{round(val, 1)}{'%' if is_pct else ''}"
    return bucketed


def answer_prior_predictions(questions: list[dict[str, Any]]) -> dict[str, str]:
    """Predict each item with its subtask's most common gold answer.

    For ``numerical_reasoning`` we bucket to 1 decimal before counting modes,
    then emit the modal bucket verbatim. This is intentionally optimistic for
    a "trivial prior": it lets the prior take advantage of any concentration
    in the answer distribution without overfitting to surface formatting.
    """
    by_subtask: dict[str, list[str]] = {}
    for q in questions:
        ans = str(q["qa"]["answer"]).strip()
        if q["subtask"] == "numerical_reasoning":
            ans = _bucket_numeric(ans)
        by_subtask.setdefault(q["subtask"], []).append(ans)

    modal: dict[str, str] = {}
    for sub, answers in by_subtask.items():
        modal[sub] = Counter(answers).most_common(1)[0][0]

    predictions: dict[str, str] = {}
    for q in questions:
        predictions[q["id"]] = modal[q["subtask"]]
    return predictions


def _is_correct(gold: str, pred: str, subtask: str, tolerance: float) -> bool:
    """jfinqa scoring: numeric tolerance for NR/CC, exact match for TR."""
    if subtask == "temporal_reasoning":
        return gold == pred
    g_raw = gold.rstrip("%").replace(",", "").strip()
    p_raw = pred.rstrip("%").replace(",", "").strip()
    try:
        gv = float(g_raw)
        pv = float(p_raw)
    except ValueError:
        return gold == pred
    if gv == 0:
        return abs(pv) < tolerance
    return abs(pv - gv) / abs(gv) < tolerance


def evaluate(
    questions: list[dict[str, Any]],
    predictions: dict[str, str],
    tolerance: float = 0.01,
) -> dict[str, Any]:
    """Score per-subtask accuracy plus overall and per-accounting-standard."""
    correct_flags: dict[str, list[tuple[str, bool]]] = {}
    for q in questions:
        gold = str(q["qa"]["answer"]).strip()
        pred = str(predictions.get(q["id"], "")).strip()
        ok = _is_correct(gold, pred, q["subtask"], tolerance)
        correct_flags.setdefault(q["subtask"], []).append((q["accounting_standard"], ok))

    by_subtask: dict[str, dict[str, Any]] = {}
    total_n = total_c = 0
    for sub, flags in correct_flags.items():
        n = len(flags)
        c = sum(1 for _, ok in flags if ok)
        by_subtask[sub] = {"accuracy_pct": round(100 * c / n, 2), "correct": c, "total": n}
        total_n += n
        total_c += c

    by_standard: dict[str, dict[str, Any]] = {}
    for sub, flags in correct_flags.items():
        for std, ok in flags:
            slot = by_standard.setdefault(std, {"correct": 0, "total": 0})
            slot["total"] += 1
            slot["correct"] += int(ok)
    for std, slot in by_standard.items():
        slot["accuracy_pct"] = round(100 * slot["correct"] / slot["total"], 2)

    return {
        "overall_pct": round(100 * total_c / total_n, 2),
        "n": total_n,
        "by_subtask": by_subtask,
        "by_accounting_standard": by_standard,
    }


def table_shuffle_predictions(*_args: Any, **_kwargs: Any) -> dict[str, str]:
    """Evidence-corruption baseline (table-shuffle).

    Owned by ``hypothesis-reasoning`` (Task #11). Stub raises NotImplementedError
    so callers and tests fail loudly until the real implementation lands.

    Design (Codex Turn 4 confirmed):
      - For each question, replace its table with a uniformly-sampled peer
        from the same subtask (different company, different period).
      - Re-run the model with the corrupted table; record accuracy.
      - Report drop in accuracy (original - corrupted) plus
        ``unchanged_answer_rate`` (fraction of items where the model's
        original and corrupted predictions match).
      - Restrict to two key models for the 2x2 paired bootstrap DID
        analysis fed into ``scripts/statistical_tests.py``:
        ``gpt-5.4-mini`` and ``gemini-2.5-flash``.
    """
    raise NotImplementedError(
        "table_shuffle is stubbed; implementation owned by hypothesis-reasoning"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        choices=["answer_prior", "table_shuffle"],
        required=True,
    )
    parser.add_argument("--data", type=Path, required=True, help="path to jfinqa final JSON")
    parser.add_argument("--output", type=Path, default=None, help="write metrics JSON here")
    parser.add_argument("--tolerance", type=float, default=0.01)
    args = parser.parse_args()

    questions = load_questions(args.data)

    if args.baseline == "answer_prior":
        predictions = answer_prior_predictions(questions)
    elif args.baseline == "table_shuffle":
        predictions = table_shuffle_predictions(questions)
    else:
        raise ValueError(f"unknown baseline: {args.baseline}")

    summary = evaluate(questions, predictions, tolerance=args.tolerance)
    output = {
        "baseline": args.baseline,
        "data": str(args.data),
        "summary": summary,
    }
    print(json.dumps(output, indent=2, ensure_ascii=False))
    if args.output:
        args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
