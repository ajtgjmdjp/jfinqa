"""Stage 4: Validate generated QA pairs and produce the final dataset.

Runs DSL program verification, answer matching, deduplication, and
diversity sampling to produce the final jfinqa benchmark file.

Usage::

    python -m scripts.pipeline.s4_validate
    # or via run_pipeline.py --stage 4
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from loguru import logger

from scripts.pipeline.config import (
    ANSWER_TOLERANCE,
    FINAL_DIR,
    GENERATED_DIR,
    MAX_COMPANY_SHARE,
    MIN_PROGRAM_STEPS,
    SUBTASK_TARGETS,
)
from scripts.pipeline.dsl import DSLError, execute_program

# ---------------------------------------------------------------------------
# Answer matching (mirrors jfinqa._metrics logic)
# ---------------------------------------------------------------------------


def _normalize(s: str) -> str:
    """Normalize an answer string for comparison."""
    import unicodedata

    s = s.strip()
    s = unicodedata.normalize("NFKC", s)
    s = s.replace("\u25b3", "-").replace("\u25b2", "-")  # △▲ → -
    s = s.replace(",", "")
    return s.lower()


def _extract_number(s: str) -> float | None:
    """Extract the first numeric value from a string."""
    import re

    s = _normalize(s)
    # Remove common suffixes
    for suffix in ["%", "円", "百万円", "千円", "億円", "兆円"]:
        s = s.replace(suffix, "")
    s = s.strip()

    match = re.search(r"-?\d+\.?\d*", s)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def _numerical_match(
    predicted: str, gold: str, tolerance: float = ANSWER_TOLERANCE
) -> bool:
    """Check if two answers match numerically within tolerance."""
    pred_num = _extract_number(predicted)
    gold_num = _extract_number(gold)

    if pred_num is None or gold_num is None:
        return _normalize(predicted) == _normalize(gold)

    if gold_num == 0:
        return abs(pred_num) < 0.001

    return abs(pred_num - gold_num) / abs(gold_num) <= tolerance


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------


def _char_ngrams(text: str, n: int = 3) -> set[str]:
    """Extract character n-grams from text."""
    text = _normalize(text)
    return {text[i : i + n] for i in range(max(0, len(text) - n + 1))}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two sets."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _deduplicate(
    questions: list[dict[str, Any]],
    threshold: float = 0.7,
) -> list[dict[str, Any]]:
    """Remove near-duplicate questions within the same company.

    Questions from different companies are never considered duplicates,
    since template-generated questions intentionally vary by company.
    """
    unique: list[dict[str, Any]] = []
    # Per-company ngram caches
    company_caches: dict[str, list[set[str]]] = defaultdict(list)

    for q in questions:
        q_text = q["qa"]["question"]
        q_ngrams = _char_ngrams(q_text)
        company = q.get("edinet_code", "unknown")

        is_dup = False
        for cached in company_caches[company]:
            if _jaccard(q_ngrams, cached) > threshold:
                is_dup = True
                break

        if not is_dup:
            unique.append(q)
            company_caches[company].append(q_ngrams)

    return unique


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def validate_question(q: dict[str, Any]) -> tuple[bool, str]:
    """Run all validation checks on a single QA pair.

    Returns (passed, reason) where reason is empty if passed.
    """
    qa = q.get("qa", {})

    # 1. Schema check
    for field in ("question", "answer", "program"):
        if field not in qa:
            return False, f"missing_field:{field}"

    if not qa["question"].strip():
        return False, "empty_question"
    if not qa["answer"].strip():
        return False, "empty_answer"

    program = qa["program"]
    if not isinstance(program, list):
        return False, "program_not_list"

    # 2. Minimum program steps
    if len(program) < MIN_PROGRAM_STEPS:
        return False, f"too_few_steps:{len(program)}"

    # 3. Execute program
    try:
        result = execute_program(program)
    except DSLError as e:
        return False, f"dsl_error:{e}"

    # 4. Format result for comparison
    answer = qa["answer"]
    if isinstance(result, bool):
        result_str = "true" if result else "false"
        # Map Japanese boolean answers to true/false
        jp_true = {"はい", "増収", "増益", "改善", "一致", "増加", "true", "yes"}
        jp_false = {"いいえ", "減収", "減益", "悪化", "不一致", "減少", "false", "no"}
        norm_answer = _normalize(answer)
        if norm_answer in jp_true:
            answer_bool = "true"
        elif norm_answer in jp_false:
            answer_bool = "false"
        else:
            answer_bool = norm_answer
        if result_str != answer_bool:
            return False, f"answer_mismatch:program={result_str},answer={answer}"
    elif isinstance(result, (int, float)):
        if math.isinf(result) or math.isnan(result):
            return False, f"invalid_result:{result}"

        # Format result to match answer format
        if "%" in answer:
            result_str = f"{result:.1f}%"
        else:
            result_str = str(result)

        if not _numerical_match(result_str, answer):
            return False, f"answer_mismatch:program={result},answer={answer}"
    else:
        result_str = str(result)
        if _normalize(result_str) != _normalize(answer):
            return False, f"answer_mismatch:program={result_str},answer={answer}"

    # 5. Check gold_evidence exists
    evidence = qa.get("gold_evidence", [])
    if not evidence:
        return False, "no_gold_evidence"

    return True, ""


# ---------------------------------------------------------------------------
# Diversity sampling
# ---------------------------------------------------------------------------


def _sample_diverse(
    questions: list[dict[str, Any]],
    target: int,
    total_questions: int,
) -> list[dict[str, Any]]:
    """Sample questions for maximum diversity across companies."""
    if len(questions) <= target:
        return questions

    max_per_company = max(3, int(total_questions * MAX_COMPANY_SHARE))

    # Group by company
    by_company: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for q in questions:
        code = q.get("edinet_code", "unknown")
        by_company[code].append(q)

    # Round-robin sampling
    result: list[dict[str, Any]] = []
    company_codes = list(by_company.keys())
    company_counts: Counter[str] = Counter()
    idx_per_company: dict[str, int] = {c: 0 for c in company_codes}

    while len(result) < target:
        added_this_round = False
        for code in company_codes:
            if len(result) >= target:
                break
            if company_counts[code] >= max_per_company:
                continue
            idx = idx_per_company[code]
            if idx < len(by_company[code]):
                result.append(by_company[code][idx])
                idx_per_company[code] = idx + 1
                company_counts[code] += 1
                added_this_round = True

        if not added_this_round:
            break

    return result


# ---------------------------------------------------------------------------
# Main validation pipeline
# ---------------------------------------------------------------------------


def run(generated_dir: Path | None = None, output_dir: Path | None = None) -> None:
    """Run Stage 4: validate and produce the final dataset."""
    gen = generated_dir or GENERATED_DIR
    out = output_dir or FINAL_DIR
    out.mkdir(parents=True, exist_ok=True)

    # Load all generated QA pairs
    gen_files = sorted(gen.glob("*.json"))
    if not gen_files:
        logger.warning(f"No generated files found in {gen}")
        return

    logger.info(f"Stage 4: Validating from {len(gen_files)} files")

    # Collect all candidates by subtask
    by_subtask: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rejected: list[dict[str, Any]] = []
    total_loaded = 0

    for gen_file in gen_files:
        data = json.loads(gen_file.read_text(encoding="utf-8"))
        questions = data if isinstance(data, list) else data.get("questions", [])

        for q in questions:
            total_loaded += 1
            passed, reason = validate_question(q)
            subtask = q.get("subtask", "numerical_reasoning")

            if passed:
                by_subtask[subtask].append(q)
            else:
                rejected.append({"question": q, "reason": reason})

    n_passed = total_loaded - len(rejected)
    logger.info(f"Loaded {total_loaded} candidates, {n_passed} passed validation")

    # Deduplicate within each subtask
    for subtask in by_subtask:
        before = len(by_subtask[subtask])
        by_subtask[subtask] = _deduplicate(by_subtask[subtask])
        after = len(by_subtask[subtask])
        if before > after:
            logger.info(f"  {subtask}: deduplicated {before} -> {after}")

    # Compute total target for diversity calculation
    total_target = sum(t["target"] for t in SUBTASK_TARGETS.values())

    # Sample with diversity
    final: list[dict[str, Any]] = []
    for subtask, targets in SUBTASK_TARGETS.items():
        available = by_subtask.get(subtask, [])
        target = targets["target"]
        sampled = _sample_diverse(available, target, total_target)
        n_avail = len(available)
        n_sel = len(sampled)
        logger.info(
            f"  {subtask}: {n_avail} available"
            f" -> {n_sel} selected (target: {target})"
        )
        final.extend(sampled)

    # Assign IDs
    counters: dict[str, int] = {
        "numerical_reasoning": 0,
        "consistency_checking": 0,
        "temporal_reasoning": 0,
    }
    prefix_map = {
        "numerical_reasoning": "nr",
        "consistency_checking": "cc",
        "temporal_reasoning": "tr",
    }

    for q in final:
        subtask = q.get("subtask", "numerical_reasoning")
        prefix = prefix_map.get(subtask, "q")
        counters[subtask] = counters.get(subtask, 0) + 1
        q["id"] = f"{prefix}_{counters[subtask]:03d}"

    # Save outputs
    final_path = out / "jfinqa_v1.json"
    final_path.write_text(
        json.dumps(final, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"Saved {len(final)} questions to {final_path}")

    rejected_path = out / "rejected.json"
    rejected_path.write_text(
        json.dumps(rejected, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info(f"Saved {len(rejected)} rejected to {rejected_path}")

    # Stats
    stats = _compute_stats(final, rejected)
    stats_path = out / "stats.json"
    stats_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info(f"Stats: {json.dumps(stats, ensure_ascii=False)}")


def _compute_stats(
    final: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute dataset statistics."""
    subtask_counts: Counter[str] = Counter()
    company_counts: Counter[str] = Counter()
    gaap_counts: Counter[str] = Counter()
    program_lengths: list[int] = []

    for q in final:
        subtask_counts[q.get("subtask", "unknown")] += 1
        company_counts[q.get("edinet_code", "unknown")] += 1
        gaap_counts[q.get("accounting_standard", "unknown")] += 1
        program_lengths.append(len(q.get("qa", {}).get("program", [])))

    rejection_reasons: Counter[str] = Counter()
    for r in rejected:
        reason = r.get("reason", "unknown")
        rejection_reasons[reason.split(":")[0]] += 1

    return {
        "total_questions": len(final),
        "total_rejected": len(rejected),
        "by_subtask": dict(subtask_counts),
        "unique_companies": len(company_counts),
        "by_accounting_standard": dict(gaap_counts),
        "avg_program_steps": sum(program_lengths) / max(1, len(program_lengths)),
        "rejection_reasons": dict(rejection_reasons),
    }


if __name__ == "__main__":
    run()
