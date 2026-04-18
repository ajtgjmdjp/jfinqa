"""Run LLM baseline evaluation on jfinqa.

Regime selection (``--regime``):

- ``R0``: no extended reasoning. OpenAI ``reasoning_effort=none``,
  Gemini ``thinking_budget=0``, Anthropic thinking disabled. Small
  ``max_output`` (2048). Ablation baseline.
- ``R1``: model-native moderate reasoning (default). OpenAI
  ``reasoning_effort=medium``, Gemini dynamic thinking (``-1``),
  Anthropic extended thinking with 4096 budget. Larger ``max_output``
  (8192). Main baseline.

Captured per question: raw response, extracted answer, correctness,
input/output/thinking token counts, truncation flag, parse success,
latency, cost (using the configured pricing table).

Usage::

    source ~/.tokens
    uv run python scripts/run_baseline.py --model gemini-2.5-flash \\
        --regime R1 --data scripts/data/final/jfinqa_lite_v1.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import median, quantiles
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

load_dotenv(ROOT / ".env")

SYSTEM_PROMPT = (
    "あなたは日本の企業の財務諸表を分析する金融アナリストです。"
    "与えられた財務データを読み、質問に正確に答えてください。"
    "最終的な答えを必ず「Answer: 値」の形式で最終行に出力してください。"
    "パーセントが問われている場合は%記号を含めてください。"
    "「はい」「いいえ」で答える場合もAnswer:の形式で出力してください。"
)


def _build_prompt(question: str, context: str) -> str:
    return (
        f"以下の財務データを読み、質問に答えてください。\n\n{context}\n\n"
        f"質問: {question}\n\n"
        f"計算過程を示した後、最終行に「Answer: 値」の形式で答えを出力してください。"
    )


def _extract_answer(response: str) -> tuple[str, bool]:
    """Return (predicted_answer, parse_success)."""
    if not response:
        return "", False
    match = re.search(r"Answer:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
    if match:
        return match.group(1).strip(), True
    lines = [line.strip() for line in response.strip().splitlines() if line.strip()]
    return (lines[-1], False) if lines else ("", False)


# ---------------------------------------------------------------------------
# Pricing (USD per 1M tokens). Updated 2026-04-18.
# When a provider charges differently for thinking tokens, the third
# entry is their thinking-token rate per 1M tokens; otherwise it equals
# the output rate.
# ---------------------------------------------------------------------------
PRICING: dict[str, tuple[float, float, float]] = {
    # OpenAI GPT-5 family
    "gpt-5.4": (1.25, 10.0, 10.0),
    "gpt-5.4-mini": (0.25, 2.0, 2.0),
    "gpt-5.4-nano": (0.05, 0.40, 0.40),
    "gpt-5.4-pro": (15.0, 120.0, 120.0),
    "gpt-5.2": (1.25, 10.0, 10.0),
    "gpt-5-mini": (0.25, 2.0, 2.0),
    "gpt-4.1": (2.0, 8.0, 8.0),
    "gpt-4.1-mini": (0.4, 1.6, 1.6),
    "gpt-4o": (2.5, 10.0, 10.0),
    "gpt-4o-mini": (0.15, 0.60, 0.60),
    # Anthropic
    "claude-sonnet-4-5": (3.0, 15.0, 15.0),
    "claude-opus-4-6": (15.0, 75.0, 75.0),
    "claude-opus-4-7": (15.0, 75.0, 75.0),
    # Google
    "gemini-2.5-pro": (1.25, 10.0, 10.0),
    "gemini-2.5-flash": (0.075, 0.30, 0.30),
    "gemini-2.5-flash-lite": (0.04, 0.15, 0.15),
    "gemini-2.0-flash": (0.10, 0.40, 0.40),
}


def _price(model: str) -> tuple[float, float, float]:
    if model in PRICING:
        return PRICING[model]
    # Fallback: assume moderate frontier cost to avoid crashing
    return (2.0, 10.0, 10.0)


@dataclass
class Attempt:
    id: str
    subtask: str
    accounting_standard: str
    company_name: str
    question: str
    gold: str
    predicted: str
    raw_response: str
    correct: bool
    parse_success: bool
    truncated: bool
    input_tokens: int
    output_tokens: int
    thinking_tokens: int
    latency_s: float
    cost_usd: float
    error: str | None = None


@dataclass
class RegimeConfig:
    name: str
    max_output: int
    openai_reasoning_effort: str | None
    gemini_thinking_budget: int | None  # None = don't set (use default)
    anthropic_thinking_budget: int | None  # None = disabled


REGIMES: dict[str, RegimeConfig] = {
    "R0": RegimeConfig(
        name="R0",
        max_output=2048,
        openai_reasoning_effort="none",
        gemini_thinking_budget=0,
        anthropic_thinking_budget=None,
    ),
    "R1": RegimeConfig(
        name="R1",
        max_output=8192,
        openai_reasoning_effort="medium",
        gemini_thinking_budget=-1,  # dynamic
        anthropic_thinking_budget=4096,
    ),
}


# ---------------------------------------------------------------------------
# Provider adapters
# ---------------------------------------------------------------------------


def call_openai(model: str, question: str, context: str, regime: RegimeConfig) -> dict[str, Any]:
    from openai import OpenAI

    client = OpenAI()
    start = time.time()

    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(question, context)},
        ],
    }
    # GPT-5 reasoning models use ``max_completion_tokens`` and ignore
    # ``temperature``; older models take the classic args.
    is_reasoning = any(model.startswith(p) for p in ("gpt-5", "o3", "o4"))
    if is_reasoning:
        kwargs["max_completion_tokens"] = regime.max_output
        if regime.openai_reasoning_effort is not None:
            kwargs["reasoning_effort"] = regime.openai_reasoning_effort
    else:
        kwargs["max_tokens"] = regime.max_output
        kwargs["temperature"] = 0.0

    resp = client.chat.completions.create(**kwargs)
    latency = time.time() - start

    choice = resp.choices[0]
    text = choice.message.content or ""
    usage = resp.usage
    input_tok = usage.prompt_tokens if usage else 0
    output_tok = usage.completion_tokens if usage else 0
    thinking_tok = 0
    if usage and hasattr(usage, "completion_tokens_details"):
        details = usage.completion_tokens_details
        if details and hasattr(details, "reasoning_tokens"):
            thinking_tok = details.reasoning_tokens or 0
    truncated = choice.finish_reason == "length"
    return {
        "text": text,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "thinking_tokens": thinking_tok,
        "latency_s": latency,
        "truncated": truncated,
    }


def call_gemini(model: str, question: str, context: str, regime: RegimeConfig) -> dict[str, Any]:
    from google import genai
    from google.genai import types

    client = genai.Client()
    start = time.time()

    config_kwargs: dict[str, Any] = {
        "temperature": 0.0,
        "max_output_tokens": regime.max_output,
    }
    # Only 2.5 models support the thinking config.
    if "2.5" in model and regime.gemini_thinking_budget is not None:
        config_kwargs["thinking_config"] = types.ThinkingConfig(
            thinking_budget=regime.gemini_thinking_budget
        )

    resp = client.models.generate_content(
        model=model,
        contents=f"{SYSTEM_PROMPT}\n\n{_build_prompt(question, context)}",
        config=types.GenerateContentConfig(**config_kwargs),
    )
    latency = time.time() - start

    text = resp.text or ""
    meta = resp.usage_metadata
    input_tok = getattr(meta, "prompt_token_count", 0) or 0 if meta else 0
    output_tok = getattr(meta, "candidates_token_count", 0) or 0 if meta else 0
    thinking_tok = getattr(meta, "thoughts_token_count", 0) or 0 if meta else 0
    candidate = resp.candidates[0] if resp.candidates else None
    truncated = False
    if candidate and hasattr(candidate, "finish_reason"):
        truncated = str(candidate.finish_reason).endswith("MAX_TOKENS")
    return {
        "text": text,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "thinking_tokens": thinking_tok,
        "latency_s": latency,
        "truncated": truncated,
    }


def call_anthropic(model: str, question: str, context: str, regime: RegimeConfig) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic()
    start = time.time()

    kwargs: dict[str, Any] = {
        "model": model,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": _build_prompt(question, context)}],
        "max_tokens": regime.max_output,
        "temperature": 0.0,
    }
    if regime.anthropic_thinking_budget is not None:
        kwargs["thinking"] = {
            "type": "enabled",
            "budget_tokens": regime.anthropic_thinking_budget,
        }

    resp = client.messages.create(**kwargs)
    latency = time.time() - start

    text_parts: list[str] = []
    thinking_tok_from_content = 0
    for block in resp.content:
        if getattr(block, "type", "") == "text":
            text_parts.append(block.text)
        elif getattr(block, "type", "") == "thinking":
            thinking_tok_from_content += len(block.thinking or "")
    text = "\n".join(text_parts)
    usage = resp.usage
    input_tok = usage.input_tokens if usage else 0
    output_tok = usage.output_tokens if usage else 0
    # Anthropic counts thinking tokens as output tokens; they are not
    # separately reported, so we leave thinking_tokens at 0 unless we
    # can derive it.
    thinking_tok = 0
    truncated = resp.stop_reason == "max_tokens"
    return {
        "text": text,
        "input_tokens": input_tok,
        "output_tokens": output_tok,
        "thinking_tokens": thinking_tok,
        "latency_s": latency,
        "truncated": truncated,
    }


MODEL_REGISTRY: dict[str, tuple[Any, str]] = {
    # OpenAI
    "gpt-4o": (call_openai, "openai"),
    "gpt-4o-mini": (call_openai, "openai"),
    "gpt-4.1": (call_openai, "openai"),
    "gpt-4.1-mini": (call_openai, "openai"),
    "gpt-5": (call_openai, "openai"),
    "gpt-5-mini": (call_openai, "openai"),
    "gpt-5.2": (call_openai, "openai"),
    "gpt-5.4": (call_openai, "openai"),
    "gpt-5.4-mini": (call_openai, "openai"),
    "gpt-5.4-nano": (call_openai, "openai"),
    # Anthropic
    "claude-sonnet-4-5": (call_anthropic, "anthropic"),
    "claude-opus-4-6": (call_anthropic, "anthropic"),
    "claude-opus-4-7": (call_anthropic, "anthropic"),
    # Google
    "gemini-2.0-flash": (call_gemini, "google"),
    "gemini-2.5-flash": (call_gemini, "google"),
    "gemini-2.5-pro": (call_gemini, "google"),
    "gemini-2.5-flash-lite": (call_gemini, "google"),
}


ENV_KEYS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def _cost(model: str, input_tok: int, output_tok: int, thinking_tok: int) -> float:
    input_price, output_price, thinking_price = _price(model)
    return (
        input_tok * input_price / 1_000_000
        + output_tok * output_price / 1_000_000
        + thinking_tok * thinking_price / 1_000_000
    )


def _summarize(attempts: list[Attempt]) -> dict[str, Any]:
    from collections import Counter, defaultdict

    def pct(x: float) -> float:
        return round(x * 100, 2)

    total = len(attempts)
    if not total:
        return {"total": 0}

    correct = sum(1 for a in attempts if a.correct)
    parsed = sum(1 for a in attempts if a.parse_success)
    truncated = sum(1 for a in attempts if a.truncated)
    errored = sum(1 for a in attempts if a.error)

    out_toks = [a.output_tokens for a in attempts]
    lats = [a.latency_s for a in attempts]
    costs = [a.cost_usd for a in attempts]

    def dist(xs: list[float]) -> dict[str, float]:
        if not xs:
            return {}
        q = quantiles(xs, n=20) if len(xs) > 1 else [xs[0]] * 19
        return {
            "mean": round(sum(xs) / len(xs), 3),
            "median": round(median(xs), 3),
            "p90": round(q[17], 3) if len(q) >= 18 else round(xs[-1], 3),
            "p95": round(q[18], 3) if len(q) >= 19 else round(xs[-1], 3),
            "max": round(max(xs), 3),
        }

    by_subtask: dict[str, dict[str, Any]] = {}
    subtask_counts: dict[str, Counter] = defaultdict(Counter)
    for a in attempts:
        c = subtask_counts[a.subtask]
        c["total"] += 1
        if a.correct:
            c["correct"] += 1
        if a.parse_success:
            c["parsed"] += 1
    for st, c in subtask_counts.items():
        by_subtask[st] = {
            "accuracy": pct(c["correct"] / c["total"]),
            "parse_success": pct(c["parsed"] / c["total"]),
            "total": c["total"],
        }

    by_accounting: dict[str, dict[str, Any]] = {}
    acc_counts: dict[str, Counter] = defaultdict(Counter)
    for a in attempts:
        c = acc_counts[a.accounting_standard]
        c["total"] += 1
        if a.correct:
            c["correct"] += 1
    for acc, c in acc_counts.items():
        by_accounting[acc] = {
            "accuracy": pct(c["correct"] / c["total"]),
            "total": c["total"],
        }

    return {
        "total": total,
        "accuracy_pct": pct(correct / total),
        "parse_success_pct": pct(parsed / total),
        "truncation_rate_pct": pct(truncated / total),
        "error_rate_pct": pct(errored / total),
        "output_tokens": dist(out_toks),
        "latency_s": dist(lats),
        "cost_total_usd": round(sum(costs), 4),
        "cost_per_correct_usd": round(sum(costs) / correct, 4) if correct else None,
        "by_subtask": by_subtask,
        "by_accounting_standard": by_accounting,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run jfinqa baseline")
    parser.add_argument("--model", required=True, choices=list(MODEL_REGISTRY.keys()))
    parser.add_argument("--regime", required=True, choices=list(REGIMES.keys()))
    parser.add_argument(
        "--data",
        default=str(ROOT / "scripts" / "data" / "final" / "jfinqa_v1.json"),
    )
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument(
        "--out-dir",
        default=str(ROOT / "scripts" / "data" / "baselines"),
    )
    args = parser.parse_args()

    regime = REGIMES[args.regime]
    call_fn, provider = MODEL_REGISTRY[args.model]
    key_name = ENV_KEYS[provider]
    if not os.environ.get(key_name):
        print(f"Error: {key_name} is not set. Run: source ~/.tokens")
        sys.exit(1)

    with open(args.data, encoding="utf-8") as f:
        rows = json.load(f)
    if args.limit > 0:
        rows = rows[: args.limit]

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    run_id = f"{args.model}__{args.regime}"
    pred_path = out_dir / f"{run_id}__predictions.json"
    metrics_path = out_dir / f"{run_id}__metrics.json"

    attempts: dict[str, Attempt] = {}
    if pred_path.exists():
        saved = json.loads(pred_path.read_text(encoding="utf-8"))
        for qid, record in saved.items():
            attempts[qid] = Attempt(**record)
        print(f"Resuming: {len(attempts)} existing attempts loaded")

    from jfinqa._metrics import numerical_match
    from jfinqa.models import QAPair, Question, Subtask, Table

    print(f"Model: {args.model}  Regime: {regime.name}  Questions: {len(rows)}")

    consecutive_errors = 0
    for i, row in enumerate(rows):
        qid = row["id"]
        if qid in attempts:
            continue
        question_obj = Question(
            id=qid,
            subtask=Subtask(row["subtask"]),
            pre_text=row["pre_text"],
            post_text=row["post_text"],
            table=Table(
                headers=row["table"]["headers"], rows=row["table"]["rows"]
            ),
            qa=QAPair(
                question=row["qa"]["question"],
                program=row["qa"]["program"],
                answer=row["qa"]["answer"],
                gold_evidence=row["qa"]["gold_evidence"],
            ),
        )
        context = question_obj.format_context()
        gold = row["qa"]["answer"]

        attempt = Attempt(
            id=qid,
            subtask=row["subtask"],
            accounting_standard=row.get("accounting_standard", ""),
            company_name=row.get("company_name", ""),
            question=row["qa"]["question"],
            gold=gold,
            predicted="",
            raw_response="",
            correct=False,
            parse_success=False,
            truncated=False,
            input_tokens=0,
            output_tokens=0,
            thinking_tokens=0,
            latency_s=0.0,
            cost_usd=0.0,
        )
        try:
            result = call_fn(args.model, row["qa"]["question"], context, regime)
            predicted, parse_ok = _extract_answer(result["text"])
            attempt.raw_response = result["text"]
            attempt.predicted = predicted
            attempt.parse_success = parse_ok
            attempt.truncated = result["truncated"]
            attempt.input_tokens = result["input_tokens"]
            attempt.output_tokens = result["output_tokens"]
            attempt.thinking_tokens = result["thinking_tokens"]
            attempt.latency_s = round(result["latency_s"], 3)
            attempt.cost_usd = round(
                _cost(
                    args.model,
                    result["input_tokens"],
                    result["output_tokens"],
                    result["thinking_tokens"],
                ),
                6,
            )
            attempt.correct = bool(parse_ok) and numerical_match(predicted, gold)
            consecutive_errors = 0
            status = "OK" if attempt.correct else ("TR" if attempt.truncated else "NG")
            print(
                f"[{i+1}/{len(rows)}] {status} {qid}: "
                f"pred={predicted!r} gold={gold!r} "
                f"tok={attempt.output_tokens}+{attempt.thinking_tokens}th "
                f"${attempt.cost_usd:.4f}"
            )
        except Exception as exc:
            attempt.error = f"{type(exc).__name__}: {exc}"
            consecutive_errors += 1
            print(f"[{i+1}/{len(rows)}] ERR {qid}: {attempt.error}")
            if consecutive_errors >= 5:
                print("5 consecutive errors, stopping.")
                break
            time.sleep(2)

        attempts[qid] = attempt

        # Persist every 10 items
        if (i + 1) % 10 == 0:
            pred_path.write_text(
                json.dumps(
                    {k: asdict(v) for k, v in attempts.items()},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        # Gentle rate-limit
        time.sleep(0.2)

    pred_path.write_text(
        json.dumps(
            {k: asdict(v) for k, v in attempts.items()},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    data_path = Path(args.data).resolve()
    try:
        data_rel = str(data_path.relative_to(ROOT))
    except ValueError:
        data_rel = str(data_path)
    metrics = {
        "model": args.model,
        "regime": regime.name,
        "data": data_rel,
        "n": len(attempts),
        "summary": _summarize(list(attempts.values())),
    }
    metrics_path.write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print()
    print("=" * 60)
    s = metrics["summary"]
    print(f"Model: {args.model}  Regime: {regime.name}")
    print(f"Accuracy: {s['accuracy_pct']}%  Parse: {s['parse_success_pct']}%  "
          f"Truncation: {s['truncation_rate_pct']}%")
    print(f"Cost: ${s['cost_total_usd']:.4f}  "
          f"Cost/correct: ${s['cost_per_correct_usd']}")
    print(f"Output tok p50/p90/p95: "
          f"{s['output_tokens'].get('median', 0)}/"
          f"{s['output_tokens'].get('p90', 0)}/"
          f"{s['output_tokens'].get('p95', 0)}")
    print(f"Predictions: {pred_path.relative_to(ROOT)}")
    print(f"Metrics:     {metrics_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
