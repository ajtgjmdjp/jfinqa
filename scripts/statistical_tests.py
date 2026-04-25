"""Paper §4.3 statistical-tests pipeline for jfinqa.

Implements Codex Q4 required fixes (R0/R1 strict definition, Holm-Bonferroni
multiple-testing correction, accuracy / parsing-failure separation, sign-flip
error taxonomy) plus the 2x2 paired bootstrap DID exploratory analysis on
two key models (gpt-5.4-mini, gemini-2.5-flash) per Codex Turn 4 guardrail.

Two pre-registered families:

* Family 1 (primary, 8 tests): cross-model + R0/R1 paired McNemar comparisons
  reproduced from the existing /tmp/jfinqa_mcnemar_results.md table.
* Family 2 (secondary, exploratory, 8 tests): per-model main-effect McNemar
  contrasts inside the 2x2 (regime x integrity) design, two key models.

Cross-diagonal contrasts (R0_orig vs R1_corr / R1_orig vs R0_corr) are
*excluded* by design --- they confound regime and integrity and are not
formally interaction tests; the interaction is reported through the bootstrap
DID estimand instead.

Holm-Bonferroni correction is applied within each family separately. The
DID bootstrap CI is reported as a separate continuous statistic without
multiplicity adjustment.

Status: skeleton. The Family 2 / DID branch requires the table-shuffle
corrupted predictions file produced by ``scripts/adversarial_baselines.py``
(Task #11). Family 1 runs end-to-end against the existing baselines.

Codex thread 019db577 verify run is required at three checkpoints
(pre-implementation family acceptance, bootstrap micro decisions,
post-integration framing consistency) before paper merge.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

# numerical_match is the canonical jfinqa accuracy judge (1% relative tolerance
# on numeric / percentage answers, exact match after normalisation otherwise).
from jfinqa._metrics import numerical_match  # type: ignore[import-not-found]


REPO_ROOT = Path(__file__).resolve().parent.parent
BASELINE_DIR = REPO_ROOT / "scripts" / "data" / "baselines_full_1000"


# ---------------------------------------------------------------------------
# 1. Loading + per-item correctness derivation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ItemOutcome:
    """Per-item outcome for a single (model, regime, integrity) condition."""

    item_id: str
    subtask: str
    accounting_standard: str
    company_name: str
    program_steps: int | None  # populated when audit data is joined; else None
    parse_ok: bool
    correct: bool


def _parse_ok(prediction: dict) -> bool:
    """Return True iff a model returned a non-empty parsed prediction.

    Accuracy and parsing-failure are reported separately per Codex Q4.
    A failed parse contributes 0 to accuracy but is *not* a reasoning error,
    so it is filtered out of any reasoning-quality interpretation.
    """
    pred = prediction.get("predicted")
    return pred is not None and str(pred).strip() != ""


def load_outcomes(predictions_path: Path) -> dict[str, ItemOutcome]:
    """Load per-item outcomes from a baseline predictions JSON.

    The baselines JSON is keyed by item id (e.g. ``nr_001``) and stores
    ``gold`` and ``predicted`` strings. Correctness is recomputed here using
    ``jfinqa._metrics.numerical_match`` for full reproducibility.
    """
    with predictions_path.open() as f:
        raw = json.load(f)
    outcomes: dict[str, ItemOutcome] = {}
    for item_id, row in raw.items():
        parse_ok = _parse_ok(row)
        gold = row.get("gold")
        predicted = row.get("predicted")
        correct = bool(parse_ok and gold is not None and numerical_match(predicted, gold))
        outcomes[item_id] = ItemOutcome(
            item_id=item_id,
            subtask=str(row.get("subtask", "")),
            accounting_standard=str(row.get("accounting_standard", "")),
            company_name=str(row.get("company_name", "")),
            program_steps=None,
            parse_ok=parse_ok,
            correct=correct,
        )
    return outcomes


# ---------------------------------------------------------------------------
# 2. Exact two-sided McNemar test
# ---------------------------------------------------------------------------


def mcnemar_exact_two_sided(b: int, c: int) -> float:
    """Exact two-sided binomial McNemar p-value on discordant pairs.

    With ``b`` items where condition A is correct and B is wrong, and ``c``
    items in the opposite direction, the discordant total ``n = b + c`` is
    distributed under H0 as Binomial(n, 0.5). Two-sided p is
    ``2 * P(X <= min(b, c))`` clipped at 1.
    """
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    cdf = sum(math.comb(n, i) for i in range(k + 1)) / (2**n)
    return min(1.0, 2.0 * cdf)


def paired_mcnemar(
    a: dict[str, ItemOutcome],
    b: dict[str, ItemOutcome],
) -> tuple[int, int, int, float]:
    """Return (n_paired, A_only_correct, B_only_correct, p_value).

    Items where either side failed to parse are *excluded* from the paired
    test, per Codex Q4 "separate accuracy and parsing failure".
    """
    common = sorted(set(a) & set(b))
    paired = [(i, a[i], b[i]) for i in common if a[i].parse_ok and b[i].parse_ok]
    a_only = sum(1 for _, ao, bo in paired if ao.correct and not bo.correct)
    b_only = sum(1 for _, ao, bo in paired if (not ao.correct) and bo.correct)
    return len(paired), a_only, b_only, mcnemar_exact_two_sided(a_only, b_only)


# ---------------------------------------------------------------------------
# 3. Holm-Bonferroni multiple-testing correction (per family)
# ---------------------------------------------------------------------------


def holm_bonferroni(p_values: Sequence[float]) -> list[float]:
    """Return Holm-adjusted p-values preserving the input order.

    Adjusted_i = max over j in {sorted_pos, sorted_pos-1, ...} of
    ``min(1, (m - rank_j) * p_(j))`` so that adjusted p-values are
    monotone-increasing along the sorted order.
    """
    m = len(p_values)
    if m == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda kv: kv[1])
    adjusted = [0.0] * m
    running_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        scaled = (m - rank) * p
        running_max = max(running_max, scaled)
        adjusted[orig_idx] = min(1.0, running_max)
    return adjusted


# ---------------------------------------------------------------------------
# 4. Family 1 (primary, 8 tests) and Family 2 (secondary 2x2, 8 tests)
# ---------------------------------------------------------------------------


# Pre-registered Family 1 comparisons (cross-model + R0/R1).
# Reproduces the eight headline rows of /tmp/jfinqa_mcnemar_results.md.
FAMILY_1_COMPARISONS: tuple[tuple[str, str, str, str], ...] = (
    ("gpt-5.4-mini", "R0", "gpt-5.4", "R0"),
    ("gpt-5.4-mini", "R0", "gpt-5.4", "R1"),
    ("gpt-5.4-mini", "R0", "gpt-5.4-mini", "R1"),
    ("gpt-5.4", "R1", "gpt-5.4", "R0"),
    ("gpt-5.4-nano", "R1", "gpt-5.4-nano", "R0"),
    ("gemini-2.5-flash", "R0", "gemini-2.5-flash", "R1"),
    ("gpt-5.4-mini", "R0", "gemini-2.5-pro", "R1"),
    ("gpt-5.4-mini", "R0", "gemini-2.5-flash", "R0"),
)

# Pre-registered Family 2 comparisons: 2 key models x 4 main-effect McNemar.
# Cross-diagonal pairs are excluded by design (see module docstring).
KEY_MODELS_FAMILY_2: tuple[str, ...] = ("gpt-5.4-mini", "gemini-2.5-flash")
MAIN_EFFECT_PAIRS: tuple[tuple[tuple[str, str], tuple[str, str]], ...] = (
    (("R0", "orig"), ("R1", "orig")),
    (("R0", "corr"), ("R1", "corr")),
    (("R0", "orig"), ("R0", "corr")),
    (("R1", "orig"), ("R1", "corr")),
)


def _baseline_path(model: str, regime: str) -> Path:
    return BASELINE_DIR / f"{model}__{regime}__predictions.json"


def run_family_1() -> list[dict]:
    """Family 1: cross-model + R0/R1 McNemar with Holm-Bonferroni correction.

    Mirrors the pre-existing analysis in /tmp/jfinqa_mcnemar_results.md but
    recomputes everything from scratch so the pipeline is reproducible end
    to end.
    """
    rows: list[dict] = []
    cache: dict[tuple[str, str], dict[str, ItemOutcome]] = {}
    p_values: list[float] = []

    for model_a, regime_a, model_b, regime_b in FAMILY_1_COMPARISONS:
        for model, regime in ((model_a, regime_a), (model_b, regime_b)):
            key = (model, regime)
            if key not in cache:
                path = _baseline_path(model, regime)
                if not path.exists():
                    raise FileNotFoundError(f"Missing baseline predictions: {path}")
                cache[key] = load_outcomes(path)

        n, a_only, b_only, p = paired_mcnemar(
            cache[(model_a, regime_a)], cache[(model_b, regime_b)]
        )
        rows.append(
            {
                "family": 1,
                "a": f"{model_a} {regime_a}",
                "b": f"{model_b} {regime_b}",
                "n_paired": n,
                "a_only_correct": a_only,
                "b_only_correct": b_only,
                "acc_diff_pt": (a_only - b_only) / n * 100 if n else 0.0,
                "p_value": p,
            }
        )
        p_values.append(p)

    for row, adj in zip(rows, holm_bonferroni(p_values), strict=True):
        row["p_holm"] = adj
    return rows


def run_family_2(corrupted_dir: Path) -> list[dict]:
    """Family 2: 2x2 main-effect McNemar on 2 key models.

    Requires corrupted predictions per (model, regime) at::

        {corrupted_dir}/{model}__{regime}__corrupted_predictions.json

    produced by ``scripts/adversarial_baselines.py`` (Task #11). Until those
    artefacts exist, this function raises FileNotFoundError and the §4.3
    paragraph notes the dependency.
    """
    rows: list[dict] = []
    cache: dict[tuple[str, str, str], dict[str, ItemOutcome]] = {}
    p_values: list[float] = []

    for model in KEY_MODELS_FAMILY_2:
        for (regime_a, integ_a), (regime_b, integ_b) in MAIN_EFFECT_PAIRS:
            for model_id, regime, integ in (
                (model, regime_a, integ_a),
                (model, regime_b, integ_b),
            ):
                key = (model_id, regime, integ)
                if key not in cache:
                    if integ == "orig":
                        path = _baseline_path(model_id, regime)
                    else:
                        path = corrupted_dir / f"{model_id}__{regime}__corrupted_predictions.json"
                    if not path.exists():
                        raise FileNotFoundError(
                            f"Missing predictions for {key}: {path}\n"
                            "Run scripts/adversarial_baselines.py first."
                        )
                    cache[key] = load_outcomes(path)

            n, a_only, b_only, p = paired_mcnemar(
                cache[(model, regime_a, integ_a)],
                cache[(model, regime_b, integ_b)],
            )
            rows.append(
                {
                    "family": 2,
                    "model": model,
                    "a": f"{regime_a}/{integ_a}",
                    "b": f"{regime_b}/{integ_b}",
                    "n_paired": n,
                    "a_only_correct": a_only,
                    "b_only_correct": b_only,
                    "acc_diff_pt": (a_only - b_only) / n * 100 if n else 0.0,
                    "p_value": p,
                }
            )
            p_values.append(p)

    for row, adj in zip(rows, holm_bonferroni(p_values), strict=True):
        row["p_holm"] = adj
    return rows


# ---------------------------------------------------------------------------
# 5. Item-level paired bootstrap DID confidence interval
# ---------------------------------------------------------------------------


def _accuracy(outcomes: Iterable[ItemOutcome]) -> float:
    items = [o for o in outcomes if o.parse_ok]
    if not items:
        return 0.0
    return sum(1 for o in items if o.correct) / len(items)


def _company_clusters(items: Sequence[ItemOutcome]) -> dict[str, list[int]]:
    clusters: dict[str, list[int]] = {}
    for idx, o in enumerate(items):
        clusters.setdefault(o.company_name or "_unknown", []).append(idx)
    return clusters


def bootstrap_did(
    r0_orig: dict[str, ItemOutcome],
    r1_orig: dict[str, ItemOutcome],
    r0_corr: dict[str, ItemOutcome],
    r1_corr: dict[str, ItemOutcome],
    *,
    n_iterations: int = 10_000,
    rng_seed: int = 20260425,
    cluster: bool = True,
) -> dict:
    """Item-level paired bootstrap CI for the DID estimand.

    The point estimand is

        DID = [acc(R1, orig) - acc(R0, orig)] - [acc(R1, corr) - acc(R0, corr)]

    Paired structure is preserved by resampling *items* (or *companies*),
    not condition-pairs. Cluster bootstrap defaults to company-level under
    the conservative-independence rationale flagged by codex-liaison.
    """
    common = sorted(set(r0_orig) & set(r1_orig) & set(r0_corr) & set(r1_corr))
    if not common:
        raise ValueError("No item ids common to all four conditions")

    items_r0_orig = [r0_orig[i] for i in common]
    items_r1_orig = [r1_orig[i] for i in common]
    items_r0_corr = [r0_corr[i] for i in common]
    items_r1_corr = [r1_corr[i] for i in common]

    point = (
        (_accuracy(items_r1_orig) - _accuracy(items_r0_orig))
        - (_accuracy(items_r1_corr) - _accuracy(items_r0_corr))
    )

    rng = random.Random(rng_seed)
    n = len(common)
    if cluster:
        clusters = _company_clusters(items_r0_orig)
        cluster_keys = list(clusters)
    samples: list[float] = []
    for _ in range(n_iterations):
        if cluster:
            picked = [rng.choice(cluster_keys) for _ in range(len(cluster_keys))]
            indices: list[int] = []
            for k in picked:
                indices.extend(clusters[k])
        else:
            indices = [rng.randrange(n) for _ in range(n)]

        def acc(items: Sequence[ItemOutcome]) -> float:
            kept = [items[i] for i in indices if items[i].parse_ok]
            return (sum(1 for o in kept if o.correct) / len(kept)) if kept else 0.0

        samples.append(
            (acc(items_r1_orig) - acc(items_r0_orig))
            - (acc(items_r1_corr) - acc(items_r0_corr))
        )

    samples.sort()
    lo = samples[int(0.025 * n_iterations)]
    hi = samples[int(0.975 * n_iterations) - 1]
    return {
        "point_estimate_pt": point * 100,
        "ci_low_pt": lo * 100,
        "ci_high_pt": hi * 100,
        "n_iterations": n_iterations,
        "n_items": n,
        "cluster_unit": "company" if cluster else "item",
    }


# ---------------------------------------------------------------------------
# 6. Sign-flip error taxonomy (Codex Q4 fix)
# ---------------------------------------------------------------------------


def sign_flip_taxonomy(
    r0: dict[str, ItemOutcome],
    r1: dict[str, ItemOutcome],
) -> dict:
    """Categorise items where R0 and R1 disagree.

    Codex Q4 fix: report which subtask / accounting standard / program-step
    bucket the regime sign-flip is concentrated in, rather than treating it
    as a single scalar effect.
    """
    common = sorted(set(r0) & set(r1))
    paired = [(r0[i], r1[i]) for i in common if r0[i].parse_ok and r1[i].parse_ok]
    bins: dict[str, dict[str, int]] = {
        "by_subtask": {},
        "by_accounting_standard": {},
    }
    for ao, bo in paired:
        if ao.correct == bo.correct:
            continue
        direction = "r0_only" if ao.correct else "r1_only"
        for axis_name, axis_value in (
            ("by_subtask", ao.subtask or "unknown"),
            ("by_accounting_standard", ao.accounting_standard or "unknown"),
        ):
            slot = f"{axis_value}__{direction}"
            bins[axis_name][slot] = bins[axis_name].get(slot, 0) + 1
    return bins


# ---------------------------------------------------------------------------
# 7. Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    family_1 = run_family_1()
    print("# Family 1 (primary, Holm-Bonferroni corrected, 8 tests)")
    for row in family_1:
        print(json.dumps(row, ensure_ascii=False))


if __name__ == "__main__":
    main()
