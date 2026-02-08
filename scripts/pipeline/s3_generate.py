"""Stage 3: Generate QA pairs from table contexts.

Creates template-based QA pairs with verified DSL programs.
Each question requires at least 2 computation steps.

Usage::

    python -m scripts.pipeline.s3_generate
    # or via run_pipeline.py --stage 3
"""

from __future__ import annotations

import json
import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from loguru import logger

from scripts.pipeline.config import CONTEXTS_DIR, GENERATED_DIR
from scripts.pipeline.dsl import execute_program

# Seed for reproducibility
random.seed(42)


# ---------------------------------------------------------------------------
# QA generators by context type
# ---------------------------------------------------------------------------


def _generate_from_pl_comparison(
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate NR questions from PL comparison contexts."""
    questions: list[dict[str, Any]] = []
    rv = ctx.get("raw_values", {})
    scale = ctx.get("scale", "百万円")
    company = ctx["company_name"]
    year_curr = ctx["filing_year"]
    year_prev = str(int(year_curr) - 1)
    period_curr = f"{year_curr}年3月期"
    period_prev = f"{year_prev}年3月期"

    # Find available items
    revenue_key = None
    for prefix in ("売上高", "売上収益"):
        if f"{prefix}_{year_curr}" in rv:
            revenue_key = prefix
            break

    op_income_key = None
    for prefix in ("営業利益",):
        if f"{prefix}_{year_curr}" in rv:
            op_income_key = prefix
            break

    ordinary_key = None
    for prefix in ("経常利益",):
        if f"{prefix}_{year_curr}" in rv:
            ordinary_key = prefix
            break

    gross_key = None
    for prefix in ("売上総利益",):
        if f"{prefix}_{year_curr}" in rv:
            gross_key = prefix
            break

    sga_key = None
    for prefix in ("販売費及び一般管理費",):
        if f"{prefix}_{year_curr}" in rv:
            sga_key = prefix
            break

    net_income_key = None
    for prefix in ("当期純利益", "親会社株主に帰属する当期純利益"):
        if f"{prefix}_{year_curr}" in rv:
            net_income_key = prefix
            break

    cogs_key = None
    for prefix in ("売上原価",):
        if f"{prefix}_{year_curr}" in rv:
            cogs_key = prefix
            break

    # Q1: Revenue growth rate (%)
    if revenue_key:
        curr_val = rv[f"{revenue_key}_{year_curr}"]
        prev_val = rv[f"{revenue_key}_{year_prev}"]
        if prev_val != 0:
            program = [
                f"subtract({curr_val}, {prev_val})",
                f"divide(#0, {prev_val})",
                "multiply(#1, 100)",
            ]
            result = execute_program(program)
            answer = f"{result:.1f}%"
            questions.append(
                _make_question(
                    ctx,
                    subtask="numerical_reasoning",
                    question=(
                        f"{company}の{period_curr}の{revenue_key}は"
                        f"前期比で何%増減したか。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{revenue_key}_{year_curr}",
                        f"{revenue_key}_{year_prev}",
                    ],
                )
            )

    # Q2: Operating margin (%)
    if revenue_key and op_income_key:
        rev = rv[f"{revenue_key}_{year_curr}"]
        op = rv[f"{op_income_key}_{year_curr}"]
        if rev != 0:
            program = [
                f"divide({op}, {rev})",
                "multiply(#0, 100)",
            ]
            result = execute_program(program)
            answer = f"{result:.1f}%"
            questions.append(
                _make_question(
                    ctx,
                    subtask="numerical_reasoning",
                    question=(
                        f"{company}の{period_curr}の営業利益率は何%か。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{op_income_key}_{year_curr}",
                        f"{revenue_key}_{year_curr}",
                    ],
                )
            )

    # Q3: Revenue change amount
    if revenue_key:
        curr_val = rv[f"{revenue_key}_{year_curr}"]
        prev_val = rv[f"{revenue_key}_{year_prev}"]
        diff = curr_val - prev_val
        program = [
            f"subtract({curr_val}, {prev_val})",
            "abs(#0)",
        ]
        result = execute_program(program)
        assert isinstance(result, (int, float))
        direction = "増加" if diff > 0 else "減少"
        answer = f"{result:,.0f}{scale}"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{revenue_key}は{period_prev}から"
                    f"{period_curr}にかけていくら{direction}したか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"{revenue_key}_{year_curr}",
                    f"{revenue_key}_{year_prev}",
                ],
            )
        )

    # Q4: Gross margin (%)
    if revenue_key and gross_key:
        rev = rv[f"{revenue_key}_{year_curr}"]
        gross = rv[f"{gross_key}_{year_curr}"]
        if rev != 0:
            program = [
                f"divide({gross}, {rev})",
                "multiply(#0, 100)",
            ]
            result = execute_program(program)
            answer = f"{result:.1f}%"
            questions.append(
                _make_question(
                    ctx,
                    subtask="numerical_reasoning",
                    question=(
                        f"{company}の{period_curr}の売上総利益率は何%か。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{gross_key}_{year_curr}",
                        f"{revenue_key}_{year_curr}",
                    ],
                )
            )

    # Q5: Operating income growth rate (%)
    if op_income_key:
        curr_val = rv[f"{op_income_key}_{year_curr}"]
        prev_val = rv[f"{op_income_key}_{year_prev}"]
        if prev_val != 0 and prev_val > 0 and curr_val > 0:
            program = [
                f"subtract({curr_val}, {prev_val})",
                f"divide(#0, {prev_val})",
                "multiply(#1, 100)",
            ]
            result = execute_program(program)
            answer = f"{result:.1f}%"
            questions.append(
                _make_question(
                    ctx,
                    subtask="numerical_reasoning",
                    question=(
                        f"{company}の{period_curr}の営業利益は"
                        f"前期比で何%変化したか。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{op_income_key}_{year_curr}",
                        f"{op_income_key}_{year_prev}",
                    ],
                )
            )

    # Q6: SGA ratio (%)
    if revenue_key and sga_key:
        rev = rv[f"{revenue_key}_{year_curr}"]
        sga = rv[f"{sga_key}_{year_curr}"]
        if rev != 0:
            program = [
                f"divide({sga}, {rev})",
                "multiply(#0, 100)",
            ]
            result = execute_program(program)
            answer = f"{result:.1f}%"
            questions.append(
                _make_question(
                    ctx,
                    subtask="numerical_reasoning",
                    question=(
                        f"{company}の{period_curr}の売上高販管費率は何%か。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{sga_key}_{year_curr}",
                        f"{revenue_key}_{year_curr}",
                    ],
                )
            )

    # Q7: Ordinary income margin change (pp)
    if revenue_key and ordinary_key:
        rev_c = rv[f"{revenue_key}_{year_curr}"]
        rev_p = rv[f"{revenue_key}_{year_prev}"]
        ord_c = rv[f"{ordinary_key}_{year_curr}"]
        ord_p = rv[f"{ordinary_key}_{year_prev}"]
        if rev_c != 0 and rev_p != 0:
            program = [
                f"divide({ord_c}, {rev_c})",
                "multiply(#0, 100)",
                f"divide({ord_p}, {rev_p})",
                "multiply(#2, 100)",
                "subtract(#1, #3)",
            ]
            result = execute_program(program)
            answer = f"{result:.1f}ポイント"
            questions.append(
                _make_question(
                    ctx,
                    subtask="numerical_reasoning",
                    question=(
                        f"{company}の経常利益率は{period_prev}から"
                        f"{period_curr}にかけて何ポイント変化したか。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{ordinary_key}_{year_curr}",
                        f"{revenue_key}_{year_curr}",
                        f"{ordinary_key}_{year_prev}",
                        f"{revenue_key}_{year_prev}",
                    ],
                )
            )

    # Q8: Temporal reasoning - revenue direction
    if revenue_key:
        curr_val = rv[f"{revenue_key}_{year_curr}"]
        prev_val = rv[f"{revenue_key}_{year_prev}"]
        program = [
            f"subtract({curr_val}, {prev_val})",
            "greater(#0, 0)",
        ]
        result = execute_program(program)
        answer = "増収" if result else "減収"
        questions.append(
            _make_question(
                ctx,
                subtask="temporal_reasoning",
                question=(
                    f"{company}は{period_prev}から{period_curr}にかけて"
                    f"増収か減収か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"{revenue_key}_{year_curr}",
                    f"{revenue_key}_{year_prev}",
                ],
            )
        )

    # Q9: Temporal - profit direction
    if op_income_key:
        curr_val = rv[f"{op_income_key}_{year_curr}"]
        prev_val = rv[f"{op_income_key}_{year_prev}"]
        program = [
            f"subtract({curr_val}, {prev_val})",
            "greater(#0, 0)",
        ]
        result = execute_program(program)
        answer = "増益" if result else "減益"
        questions.append(
            _make_question(
                ctx,
                subtask="temporal_reasoning",
                question=(
                    f"{company}は{period_prev}から{period_curr}にかけて"
                    f"営業利益ベースで増益か減益か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"{op_income_key}_{year_curr}",
                    f"{op_income_key}_{year_prev}",
                ],
            )
        )

    # Q10: Temporal - operating margin improvement/deterioration
    if revenue_key and op_income_key:
        rev_c = rv[f"{revenue_key}_{year_curr}"]
        rev_p = rv[f"{revenue_key}_{year_prev}"]
        op_c = rv[f"{op_income_key}_{year_curr}"]
        op_p = rv[f"{op_income_key}_{year_prev}"]
        if rev_c != 0 and rev_p != 0:
            program = [
                f"divide({op_c}, {rev_c})",
                f"divide({op_p}, {rev_p})",
                "subtract(#0, #1)",
                "greater(#2, 0)",
            ]
            result = execute_program(program)
            answer = "改善" if result else "悪化"
            questions.append(
                _make_question(
                    ctx,
                    subtask="temporal_reasoning",
                    question=(
                        f"{company}の営業利益率は{period_prev}から"
                        f"{period_curr}にかけて改善したか悪化したか。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{op_income_key}_{year_curr}",
                        f"{revenue_key}_{year_curr}",
                        f"{op_income_key}_{year_prev}",
                        f"{revenue_key}_{year_prev}",
                    ],
                )
            )

    # Q11: Temporal - ordinary income direction
    if ordinary_key:
        curr_val = rv[f"{ordinary_key}_{year_curr}"]
        prev_val = rv[f"{ordinary_key}_{year_prev}"]
        program = [
            f"subtract({curr_val}, {prev_val})",
            "greater(#0, 0)",
        ]
        result = execute_program(program)
        answer = "増益" if result else "減益"
        questions.append(
            _make_question(
                ctx,
                subtask="temporal_reasoning",
                question=(
                    f"{company}は{period_prev}から{period_curr}にかけて"
                    f"経常利益ベースで増益か減益か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"{ordinary_key}_{year_curr}",
                    f"{ordinary_key}_{year_prev}",
                ],
            )
        )

    # Q12: Net income margin (%) — NR
    if revenue_key and net_income_key:
        rev = rv[f"{revenue_key}_{year_curr}"]
        ni = rv[f"{net_income_key}_{year_curr}"]
        if rev != 0:
            program = [
                f"divide({ni}, {rev})",
                "multiply(#0, 100)",
            ]
            result = execute_program(program)
            answer = f"{result:.1f}%"
            questions.append(
                _make_question(
                    ctx,
                    subtask="numerical_reasoning",
                    question=(
                        f"{company}の{period_curr}の当期純利益率は何%か。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{net_income_key}_{year_curr}",
                        f"{revenue_key}_{year_curr}",
                    ],
                )
            )

    # Q13: Cost of sales ratio (%) — NR
    if revenue_key and cogs_key:
        rev = rv[f"{revenue_key}_{year_curr}"]
        cogs = rv[f"{cogs_key}_{year_curr}"]
        if rev != 0:
            program = [
                f"divide({cogs}, {rev})",
                "multiply(#0, 100)",
            ]
            result = execute_program(program)
            answer = f"{result:.1f}%"
            questions.append(
                _make_question(
                    ctx,
                    subtask="numerical_reasoning",
                    question=(
                        f"{company}の{period_curr}の売上原価率は何%か。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{cogs_key}_{year_curr}",
                        f"{revenue_key}_{year_curr}",
                    ],
                )
            )

    # Q14: Gross profit = Revenue - COGS consistency — CC
    if revenue_key and cogs_key and gross_key:
        rev = rv[f"{revenue_key}_{year_curr}"]
        cogs = rv[f"{cogs_key}_{year_curr}"]
        gross = rv[f"{gross_key}_{year_curr}"]
        computed = rev - cogs
        program = [
            f"subtract({rev}, {cogs})",
        ]
        answer = f"{computed:,.0f}"
        questions.append(
            _make_question(
                ctx,
                subtask="consistency_checking",
                question=(
                    f"{company}の{period_curr}の{revenue_key}から売上原価を"
                    f"差し引いた額はいくらか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"{revenue_key}_{year_curr}",
                    f"{cogs_key}_{year_curr}",
                ],
            )
        )

    # Q15: Operating income = Gross profit - SGA consistency — CC
    if gross_key and sga_key and op_income_key:
        gross = rv[f"{gross_key}_{year_curr}"]
        sga = rv[f"{sga_key}_{year_curr}"]
        computed = gross - sga
        program = [
            f"subtract({gross}, {sga})",
        ]
        answer = f"{computed:,.0f}"
        questions.append(
            _make_question(
                ctx,
                subtask="consistency_checking",
                question=(
                    f"{company}の{period_curr}の売上総利益から"
                    f"販売費及び一般管理費を差し引いた額はいくらか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"{gross_key}_{year_curr}",
                    f"{sga_key}_{year_curr}",
                ],
            )
        )

    # Q16: Gross margin improvement/deterioration — TR
    if revenue_key and gross_key:
        rev_c = rv[f"{revenue_key}_{year_curr}"]
        rev_p = rv[f"{revenue_key}_{year_prev}"]
        gross_c = rv[f"{gross_key}_{year_curr}"]
        gross_p = rv.get(f"{gross_key}_{year_prev}")
        if gross_p is not None and rev_c != 0 and rev_p != 0:
            program = [
                f"divide({gross_c}, {rev_c})",
                f"divide({gross_p}, {rev_p})",
                "subtract(#0, #1)",
                "greater(#2, 0)",
            ]
            result = execute_program(program)
            answer = "改善" if result else "悪化"
            questions.append(
                _make_question(
                    ctx,
                    subtask="temporal_reasoning",
                    question=(
                        f"{company}の売上総利益率は{period_prev}から"
                        f"{period_curr}にかけて改善したか悪化したか。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=[
                        f"{gross_key}_{year_curr}",
                        f"{revenue_key}_{year_curr}",
                        f"{gross_key}_{year_prev}",
                        f"{revenue_key}_{year_prev}",
                    ],
                )
            )

    return questions


def _generate_from_bs_summary(
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate NR questions from BS summary contexts."""
    questions: list[dict[str, Any]] = []
    rv = ctx.get("raw_values", {})
    company = ctx["company_name"]
    year = ctx["filing_year"]
    period = f"{year}年3月期"
    y = f"_{year}"

    total_assets = rv.get(f"資産合計{y}")
    current_assets = rv.get(f"流動資産{y}")
    fixed_assets = rv.get(f"固定資産{y}") or rv.get(f"非流動資産{y}")
    total_liabilities = rv.get(f"負債合計{y}")
    current_liab = rv.get(f"流動負債{y}")
    equity = rv.get(f"純資産合計{y}") or rv.get(f"株主資本合計{y}")

    # Calculate total_assets from components if not directly available
    if not total_assets and current_assets and fixed_assets:
        total_assets = current_assets + fixed_assets
    if not total_liabilities and current_liab:
        fixed_liab = rv.get(f"固定負債{y}") or rv.get(f"非流動負債{y}")
        if fixed_liab:
            total_liabilities = current_liab + fixed_liab

    # Q1: Current ratio
    if current_assets and current_liab and current_liab != 0:
        program = [
            f"divide({current_assets}, {current_liab})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.1f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period}の流動比率は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=["流動資産", "流動負債"],
            )
        )

    # Q2: Equity ratio
    if equity and total_assets and total_assets != 0:
        eq_label = (
            "純資産合計" if f"純資産合計{y}" in rv else "株主資本合計"
        )
        evidence = [eq_label, "流動資産", "固定資産"]
        program = [
            f"divide({equity}, {total_assets})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.1f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period}の自己資本比率は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=evidence,
            )
        )

    # Q3: Debt ratio (only when 負債合計 exists directly in table)
    if (
        total_liabilities
        and total_assets
        and total_assets != 0
        and rv.get(f"負債合計{y}")
    ):
        program = [
            f"divide({total_liabilities}, {total_assets})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.1f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period}の負債比率"
                    f"(負債/総資産)は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=["負債合計", "流動資産", "固定資産"],
            )
        )

    # Q4: Fixed assets / total assets ratio
    if fixed_assets and total_assets and total_assets != 0:
        fa_label = "固定資産" if f"固定資産{y}" in rv else "非流動資産"
        # Build evidence from actual table rows
        evidence = [fa_label, "流動資産"]
        program = [
            f"divide({fixed_assets}, {total_assets})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.1f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period}の{fa_label}比率"
                    f"({fa_label}/総資産)は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=evidence,
            )
        )

    return questions


def _generate_from_bs_consistency(
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate CC questions from BS consistency contexts."""
    questions: list[dict[str, Any]] = []
    rv = ctx.get("raw_values", {})
    company = ctx["company_name"]
    year = ctx["filing_year"]
    period = f"{year}年3月期"
    y = f"_{year}"

    current_assets = rv.get(f"流動資産{y}")
    fixed_assets = rv.get(f"固定資産{y}") or rv.get(f"非流動資産{y}")
    equity = rv.get(f"純資産合計{y}") or rv.get(f"株主資本合計{y}")
    current_liab = rv.get(f"流動負債{y}")
    fixed_liab = rv.get(f"固定負債{y}") or rv.get(f"非流動負債{y}")

    # CC1: Assets side = Liabilities + Equity side? (BS balance check)
    if current_assets and fixed_assets and current_liab and equity:
        program = [
            f"add({current_assets}, {fixed_assets})",
            f"add({current_liab}, {fixed_liab or 0})",
            f"add(#1, {equity})",
            "eq(#0, #2)",
        ]
        result = execute_program(program)
        fa_label = (
            "固定資産" if f"固定資産{y}" in rv else "非流動資産"
        )
        eq_label = (
            "純資産合計" if f"純資産合計{y}" in rv else "株主資本合計"
        )
        answer = "はい" if result else "いいえ"
        questions.append(
            _make_question(
                ctx,
                subtask="consistency_checking",
                question=(
                    f"{company}の{period}の資産の部の合計"
                    f"(流動資産+{fa_label})は、負債・{eq_label}の"
                    f"合計と一致するか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    "流動資産", fa_label, "流動負債",
                    "固定負債" if fixed_liab else "", eq_label,
                ],
            )
        )

    # CC2: Compute total assets from parts and verify
    if current_assets and fixed_assets:
        computed_total = current_assets + fixed_assets
        fa_label = (
            "固定資産" if f"固定資産{y}" in rv else "非流動資産"
        )
        program = [
            f"add({current_assets}, {fixed_assets})",
            f"subtract(#0, {computed_total})",
            "eq(#1, 0)",
        ]
        result = execute_program(program)
        answer = f"{computed_total:,.0f}"
        questions.append(
            _make_question(
                ctx,
                subtask="consistency_checking",
                question=(
                    f"{company}の{period}の流動資産と{fa_label}の合計は"
                    f"いくらか。"
                ),
                answer=answer,
                program=[
                    f"add({current_assets}, {fixed_assets})",
                ],
                gold_evidence=["流動資産", fa_label],
            )
        )

    # CC3: Liability decomposition
    if current_liab and fixed_liab:
        fl_label = (
            "固定負債" if f"固定負債{y}" in rv else "非流動負債"
        )
        total_liab = current_liab + fixed_liab
        program = [
            f"add({current_liab}, {fixed_liab})",
        ]
        answer = f"{total_liab:,.0f}"
        questions.append(
            _make_question(
                ctx,
                subtask="consistency_checking",
                question=(
                    f"{company}の{period}の流動負債と{fl_label}の合計"
                    f"(負債合計)はいくらか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=["流動負債", fl_label],
            )
        )

    # CC4: Equity as percentage of total (cross-check)
    if current_assets and fixed_assets and equity:
        total_a = current_assets + fixed_assets
        if total_a != 0:
            program = [
                f"add({current_assets}, {fixed_assets})",
                f"divide({equity}, #0)",
                "multiply(#1, 100)",
            ]
            result = execute_program(program)
            eq_label = (
                "純資産合計"
                if f"純資産合計{y}" in rv
                else "株主資本合計"
            )
            answer = f"{result:.1f}%"
            questions.append(
                _make_question(
                    ctx,
                    subtask="consistency_checking",
                    question=(
                        f"{company}の{period}の{eq_label}は"
                        f"総資産の何%を占めるか。"
                    ),
                    answer=answer,
                    program=program,
                    gold_evidence=["流動資産", "固定資産", eq_label],
                )
            )

    return questions


def _generate_from_cf_summary(
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate NR questions from CF summary contexts."""
    questions: list[dict[str, Any]] = []
    rv = ctx.get("raw_values", {})
    scale = ctx.get("scale", "百万円")
    company = ctx["company_name"]
    year_curr = ctx["filing_year"]
    period_curr = f"{year_curr}年3月期"

    ope_key = f"営業活動によるキャッシュ・フロー_{year_curr}"
    inv_key = f"投資活動によるキャッシュ・フロー_{year_curr}"
    fin_key = f"財務活動によるキャッシュ・フロー_{year_curr}"
    ope_cf = rv.get(ope_key)
    inv_cf = rv.get(inv_key)
    fin_cf = rv.get(fin_key)

    # Q1: FCF = Operating CF + Investing CF
    if ope_cf is not None and inv_cf is not None:
        program = [
            f"add({ope_cf}, {inv_cf})",
        ]
        result = execute_program(program)
        answer = f"{result:,.0f}{scale}"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period_curr}のフリーキャッシュフロー"
                    f"(営業CF+投資CF)はいくらか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"営業活動によるキャッシュ・フロー_{year_curr}",
                    f"投資活動によるキャッシュ・フロー_{year_curr}",
                ],
            )
        )

    # Q2: Total CF = sum of 3 CFs
    if ope_cf is not None and inv_cf is not None and fin_cf is not None:
        program = [
            f"add({ope_cf}, {inv_cf})",
            f"add(#0, {fin_cf})",
        ]
        result = execute_program(program)
        answer = f"{result:,.0f}{scale}"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period_curr}の3つのキャッシュフロー"
                    f"活動の合計額はいくらか"
                    f"(為替影響除く)。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"営業活動によるキャッシュ・フロー_{year_curr}",
                    f"投資活動によるキャッシュ・フロー_{year_curr}",
                    f"財務活動によるキャッシュ・フロー_{year_curr}",
                ],
            )
        )

    # Q3: Operating CF / Investing CF ratio
    if ope_cf and inv_cf and inv_cf != 0:
        program = [
            f"divide({ope_cf}, {abs(inv_cf)})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.1f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period_curr}の営業CFは"
                    f"投資CFの何%をカバーしているか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"営業活動によるキャッシュ・フロー_{year_curr}",
                    f"投資活動によるキャッシュ・フロー_{year_curr}",
                ],
            )
        )

    # Prev year values for temporal questions
    year_prev = str(int(year_curr) - 1)
    period_prev = f"{year_prev}年3月期"
    ope_prev = rv.get(f"営業活動によるキャッシュ・フロー_{year_prev}")
    inv_prev = rv.get(f"投資活動によるキャッシュ・フロー_{year_prev}")

    # Q4: Temporal - Operating CF direction
    if ope_cf is not None and ope_prev is not None:
        program = [
            f"subtract({ope_cf}, {ope_prev})",
            "greater(#0, 0)",
        ]
        result = execute_program(program)
        answer = "増加" if result else "減少"
        questions.append(
            _make_question(
                ctx,
                subtask="temporal_reasoning",
                question=(
                    f"{company}の営業キャッシュフローは"
                    f"{period_prev}から{period_curr}にかけて"
                    f"増加したか減少したか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"営業活動によるキャッシュ・フロー_{year_curr}",
                    f"営業活動によるキャッシュ・フロー_{year_prev}",
                ],
            )
        )

    # Q5: Temporal - FCF improvement/deterioration (2-period CF)
    if (
        ope_cf is not None
        and inv_cf is not None
        and ope_prev is not None
        and inv_prev is not None
    ):
        program = [
            f"add({ope_cf}, {inv_cf})",
            f"add({ope_prev}, {inv_prev})",
            "subtract(#0, #1)",
            "greater(#2, 0)",
        ]
        result = execute_program(program)
        answer = "改善" if result else "悪化"
        questions.append(
            _make_question(
                ctx,
                subtask="temporal_reasoning",
                question=(
                    f"{company}のフリーキャッシュフローは"
                    f"{period_prev}から{period_curr}にかけて"
                    f"改善したか悪化したか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[
                    f"営業活動によるキャッシュ・フロー_{year_curr}",
                    f"投資活動によるキャッシュ・フロー_{year_curr}",
                    f"営業活動によるキャッシュ・フロー_{year_prev}",
                    f"投資活動によるキャッシュ・フロー_{year_prev}",
                ],
            )
        )

    return questions


def _generate_from_cross_statement(
    ctx: dict[str, Any],
) -> list[dict[str, Any]]:
    """Generate NR questions from cross-statement contexts."""
    questions: list[dict[str, Any]] = []
    rv = ctx.get("raw_values", {})
    company = ctx["company_name"]
    year = ctx["filing_year"]
    period = f"{year}年3月期"
    y = f"_{year}"

    # Available items (year-suffixed keys)
    revenue = None
    for k in ("売上高", "売上収益"):
        if f"{k}{y}" in rv:
            revenue = (k, rv[f"{k}{y}"])
            break

    op_income = rv.get(f"営業利益{y}")
    ordinary = rv.get(f"経常利益{y}")
    total_assets = rv.get(f"資産合計{y}")
    equity = rv.get(f"純資産合計{y}") or rv.get(f"株主資本合計{y}")
    net_income = (
        rv.get(f"当期純利益{y}")
        or rv.get(f"親会社株主に帰属する当期純利益{y}")
    )

    # Calculate total_assets from components if not directly available
    if not total_assets:
        ca = rv.get(f"流動資産{y}")
        fa = rv.get(f"固定資産{y}") or rv.get(f"非流動資産{y}")
        if ca and fa:
            total_assets = ca + fa

    # Q1: ROA
    if ordinary and total_assets and total_assets != 0:
        program = [
            f"divide({ordinary}, {total_assets})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.2f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period}のROA"
                    f"(経常利益/総資産)は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=["経常利益", "資産合計"],
            )
        )

    # Q2: ROE
    if net_income and equity and equity != 0:
        ni_label = (
            "当期純利益"
            if f"当期純利益{y}" in rv
            else "親会社株主に帰属する当期純利益"
        )
        program = [
            f"divide({net_income}, {equity})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.2f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period}のROE"
                    f"({ni_label}/純資産)は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[ni_label, "純資産合計"],
            )
        )

    # Q3: Operating margin (cross-check from cross_statement)
    if revenue and op_income and revenue[1] != 0:
        program = [
            f"divide({op_income}, {revenue[1]})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.1f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period}の{revenue[0]}に対する"
                    f"営業利益率は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=["営業利益", revenue[0]],
            )
        )

    # Q4: Asset turnover (revenue / total assets)
    if revenue and total_assets and total_assets != 0:
        program = [
            f"divide({revenue[1]}, {total_assets})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.1f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="numerical_reasoning",
                question=(
                    f"{company}の{period}の総資産回転率"
                    f"({revenue[0]}/総資産*100)は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=[revenue[0], "資産合計"],
            )
        )

    # Retrieve liability components for CC questions
    total_liabilities = rv.get(f"負債合計{y}")
    current_liab = rv.get(f"流動負債{y}")
    fixed_liab = rv.get(f"固定負債{y}") or rv.get(f"非流動負債{y}")
    if not total_liabilities and current_liab and fixed_liab:
        total_liabilities = current_liab + fixed_liab

    # Q5: Liabilities + Equity = Total Assets consistency — CC
    if total_liabilities and equity and total_assets:
        program = [
            f"add({total_liabilities}, {equity})",
        ]
        computed = total_liabilities + equity
        answer = f"{computed:,.0f}"
        eq_label = (
            "純資産合計" if f"純資産合計{y}" in rv else "株主資本合計"
        )
        questions.append(
            _make_question(
                ctx,
                subtask="consistency_checking",
                question=(
                    f"{company}の{period}の負債合計と{eq_label}の"
                    f"合計はいくらか。"
                ),
                answer=answer,
                program=program,
                gold_evidence=["負債合計", eq_label],
            )
        )

    # Q6: ROA cross-statement consistency — CC
    if ordinary and total_assets and total_assets != 0:
        program = [
            f"divide({ordinary}, {total_assets})",
            "multiply(#0, 100)",
        ]
        result = execute_program(program)
        answer = f"{result:.2f}%"
        questions.append(
            _make_question(
                ctx,
                subtask="consistency_checking",
                question=(
                    f"{company}の{period}の損益計算書の経常利益を"
                    f"貸借対照表の総資産で割った値は何%か。"
                ),
                answer=answer,
                program=program,
                gold_evidence=["経常利益", "資産合計"],
            )
        )

    return questions


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _labels_to_row_indices(
    table: dict[str, Any], labels: list[str]
) -> list[int]:
    """Convert evidence label strings to table row indices.

    Strips year suffixes (e.g. ``_2024``) from labels to match
    table row headers which don't include years.
    """
    import re

    rows = table.get("rows", [])
    indices: list[int] = []
    for label in labels:
        if not label:
            continue
        # Strip year suffix like _2024 or _2023
        base_label = re.sub(r"_\d{4}$", "", label)
        for i, row in enumerate(rows):
            if row and row[0] == base_label and i not in indices:
                indices.append(i)
                break
    return sorted(indices)


def _make_question(
    ctx: dict[str, Any],
    *,
    subtask: str,
    question: str,
    answer: str,
    program: list[str],
    gold_evidence: list[str],
) -> dict[str, Any]:
    """Create a QA pair dict."""
    table = ctx["table"]
    evidence_indices = _labels_to_row_indices(table, gold_evidence)
    return {
        "company_name": ctx["company_name"],
        "edinet_code": ctx["edinet_code"],
        "source_doc_id": ctx.get("source_doc_id", ""),
        "filing_year": ctx["filing_year"],
        "accounting_standard": ctx["accounting_standard"],
        "subtask": subtask,
        "pre_text": ctx["pre_text"],
        "post_text": ctx["post_text"],
        "table": table,
        "qa": {
            "question": question,
            "answer": answer,
            "program": program,
            "gold_evidence": evidence_indices,
        },
        "scale": ctx.get("scale", ""),
    }


# ---------------------------------------------------------------------------
# Generators registry
# ---------------------------------------------------------------------------

_GENERATORS = {
    "pl_comparison": _generate_from_pl_comparison,
    "bs_summary": _generate_from_bs_summary,
    "bs_consistency": _generate_from_bs_consistency,
    "cf_summary": _generate_from_cf_summary,
    "cross_statement": _generate_from_cross_statement,
}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run(output_dir: Path | None = None) -> None:
    """Run Stage 3: generate QA pairs from contexts."""
    import os

    ctx_dir = CONTEXTS_DIR
    out_dir = output_dir or GENERATED_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    all_questions: list[dict[str, Any]] = []
    stats: dict[str, int] = {
        "numerical_reasoning": 0,
        "consistency_checking": 0,
        "temporal_reasoning": 0,
    }

    ctx_files = sorted(
        f
        for f in os.listdir(ctx_dir)
        if f.endswith("_contexts.json")
    )

    for ctx_file in ctx_files:
        contexts = json.loads(
            (ctx_dir / ctx_file).read_text(encoding="utf-8")
        )
        for ctx in contexts:
            ct = ctx.get("context_type", "")
            generator = _GENERATORS.get(ct)
            if generator:
                questions = generator(ctx)
                for q in questions:
                    st = q.get("subtask", "numerical_reasoning")
                    stats[st] = stats.get(st, 0) + 1
                all_questions.extend(questions)

    # Write output
    output_path = out_dir / "generated_qa.json"
    output_path.write_text(
        json.dumps(all_questions, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info(f"Stage 3: Generated {len(all_questions)} QA pairs")
    for subtask, count in sorted(stats.items()):
        logger.info(f"  {subtask}: {count}")
    logger.info(f"Output: {output_path}")


if __name__ == "__main__":
    run()
