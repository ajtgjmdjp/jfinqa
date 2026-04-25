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
import copy
import json
import random
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


def write_table_shuffled_dataset(
    questions: list[dict[str, Any]],
    *,
    rng_seed: int = 20260425,
) -> list[dict[str, Any]]:
    """Return a row-permuted copy of the dataset.

    Codex Turn 4 confirmed table-shuffle as the **primary** evidence-dependence
    proof, prioritised over answer-prior and regex/XBRL lookup. Implementation:
    permute the order of *data rows* inside each item's ``table`` (headers and
    column structure preserved) so that any model that genuinely retrieves the
    correct row by name remains correct, while a model that exploits positional
    or template priors degrades.

    The output JSON has the same schema as the source --- existing
    ``scripts/run_baseline.py`` invocations work unchanged. Permutation is
    deterministic given ``rng_seed``.

    The downstream paired DID analysis (``[(R1_orig - R0_orig) -
    (R1_corr - R0_corr)]``) is computed by ``scripts/statistical_tests.py``
    on the two key models (``gpt-5.4-mini``, ``gemini-2.5-flash``).
    """
    rng = random.Random(rng_seed)
    perturbed: list[dict[str, Any]] = []
    for q in questions:
        new_q = copy.deepcopy(q)
        table = new_q.get("table")
        if isinstance(table, dict):
            rows = list(table.get("rows", []))
            if len(rows) > 1:
                # Repeated shuffles can leave rows in their original order with
                # non-trivial probability for short tables. Loop until we land
                # on a non-identity permutation, falling back to the original
                # for tables of length <= 1 where any "shuffle" is a no-op.
                shuffled = list(rows)
                for _ in range(10):
                    rng.shuffle(shuffled)
                    if shuffled != rows:
                        break
                table = {**table, "rows": shuffled}
                new_q["table"] = table
        perturbed.append(new_q)
    return perturbed


def table_shuffle_predictions(*_args: Any, **_kwargs: Any) -> dict[str, str]:
    """Evidence-corruption baseline (table-shuffle), prediction step.

    Table-shuffling itself is offline (see ``write_table_shuffled_dataset``);
    actual model predictions on the perturbed dataset are produced by
    ``scripts/run_baseline.py`` against the perturbed JSON. This entry point
    is preserved so the CLI plumbing matches the Codex Q10 MVP catalogue, but
    it raises so callers do not accidentally treat row-permutation as the
    final answer.
    """
    raise NotImplementedError(
        "table_shuffle does not predict directly; emit the perturbed dataset "
        "via write_table_shuffled_dataset and re-run scripts/run_baseline.py "
        "on it for each (model, regime) pair."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline",
        choices=["answer_prior", "table_shuffle", "write_table_shuffled"],
        required=True,
        help=(
            "answer_prior: subtask-modal predictions; "
            "table_shuffle: prediction stub (use write_table_shuffled instead); "
            "write_table_shuffled: emit row-permuted dataset for re-evaluation"
        ),
    )
    parser.add_argument("--data", type=Path, required=True, help="path to jfinqa final JSON")
    parser.add_argument("--output", type=Path, default=None, help="write metrics JSON here")
    parser.add_argument("--tolerance", type=float, default=0.01)
    parser.add_argument(
        "--seed",
        type=int,
        default=20260425,
        help="rng seed for write_table_shuffled (deterministic output)",
    )
    args = parser.parse_args()

    questions = load_questions(args.data)

    if args.baseline == "write_table_shuffled":
        out_path = args.output or args.data.with_name(
            args.data.stem + "__table_shuffled.json"
        )
        perturbed = write_table_shuffled_dataset(questions, rng_seed=args.seed)
        out_path.write_text(json.dumps(perturbed, indent=2, ensure_ascii=False))
        print(json.dumps(
            {
                "wrote": str(out_path),
                "n_items": len(perturbed),
                "rng_seed": args.seed,
            },
            indent=2,
            ensure_ascii=False,
        ))
        return

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
