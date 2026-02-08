"""Run LLM baseline evaluation on jfinqa.

Usage:
    # Set API keys in .env file, then:
    uv run python scripts/run_baseline.py --model gpt-4o
    uv run python scripts/run_baseline.py --model gpt-4o-mini
    uv run python scripts/run_baseline.py --model gemini-2.0-flash
    uv run python scripts/run_baseline.py --model claude-3-5-sonnet-20241022

Outputs:
    scripts/data/baselines/{model_name}_predictions.json
    scripts/data/baselines/{model_name}_results.json
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

# Load API keys from .env (gitignored)
load_dotenv(Path(__file__).parent.parent / ".env")

# ---------------------------------------------------------------------------
# Model adapters
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "あなたは日本の企業の財務諸表を分析する金融アナリストです。"
    "与えられた財務データを読み、質問に正確に答えてください。"
    "最終的な答えを必ず「Answer: 値」の形式で最終行に出力してください。"
    "パーセントが問われている場合は%記号を含めてください。"
    "「はい」「いいえ」で答える場合もAnswer:の形式で出力してください。"
)


def _build_prompt(question_text: str, context: str) -> str:
    return (
        f"以下の財務データを読み、質問に答えてください。\n\n"
        f"{context}\n\n"
        f"質問: {question_text}\n\n"
        f"計算過程を示した後、最終行に「Answer: 値」の形式で答えを出力してください。"
    )


def _extract_answer(response: str) -> str:
    """Extract the answer from LLM response."""
    # Look for "Answer: ..." pattern
    match = re.search(r"Answer:\s*(.+?)(?:\n|$)", response, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: last line
    lines = [l.strip() for l in response.strip().splitlines() if l.strip()]
    return lines[-1] if lines else ""


def call_openai(model: str, question: str, context: str) -> str:
    from openai import OpenAI

    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_prompt(question, context)},
        ],
        temperature=0.0,
        max_tokens=512,
    )
    return resp.choices[0].message.content or ""


def call_anthropic(model: str, question: str, context: str) -> str:
    from anthropic import Anthropic

    client = Anthropic()
    resp = client.messages.create(
        model=model,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": _build_prompt(question, context)},
        ],
        temperature=0.0,
        max_tokens=512,
    )
    return resp.content[0].text


def call_gemini(model: str, question: str, context: str) -> str:
    from google import genai

    client = genai.Client()
    resp = client.models.generate_content(
        model=model,
        contents=f"{SYSTEM_PROMPT}\n\n{_build_prompt(question, context)}",
        config=genai.types.GenerateContentConfig(
            temperature=0.0,
            max_output_tokens=512,
        ),
    )
    return resp.text or ""


# Model name -> (call function, provider)
MODEL_REGISTRY: dict[str, tuple] = {
    # OpenAI
    "gpt-4o": (call_openai, "openai"),
    "gpt-4o-mini": (call_openai, "openai"),
    "gpt-4.1": (call_openai, "openai"),
    "gpt-4.1-mini": (call_openai, "openai"),
    # Anthropic
    "claude-3-5-sonnet-20241022": (call_anthropic, "anthropic"),
    "claude-3-5-haiku-20241022": (call_anthropic, "anthropic"),
    # Google
    "gemini-2.0-flash": (call_gemini, "google"),
    "gemini-2.5-flash-preview-04-17": (call_gemini, "google"),
}


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run LLM baseline on jfinqa")
    parser.add_argument(
        "--model",
        required=True,
        choices=list(MODEL_REGISTRY.keys()),
        help="Model to evaluate",
    )
    parser.add_argument(
        "--limit", type=int, default=0, help="Limit number of questions (0=all)"
    )
    parser.add_argument(
        "--data",
        default=str(Path(__file__).parent / "data" / "final" / "jfinqa_v1.json"),
        help="Path to dataset JSON",
    )
    args = parser.parse_args()

    # Check API key
    call_fn, provider = MODEL_REGISTRY[args.model]
    env_keys = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    key_name = env_keys[provider]
    if not os.environ.get(key_name):
        print(f"Error: {key_name} environment variable is required")
        sys.exit(1)

    # Load data
    with open(args.data, encoding="utf-8") as f:
        raw = json.load(f)

    if args.limit > 0:
        raw = raw[: args.limit]

    print(f"Model: {args.model}")
    print(f"Questions: {len(raw)}")
    print()

    # Output directory
    out_dir = Path(__file__).parent / "data" / "baselines"
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_name = args.model.replace("/", "_")
    pred_path = out_dir / f"{safe_name}_predictions.json"
    result_path = out_dir / f"{safe_name}_results.json"

    # Load existing predictions (for resume)
    predictions: dict[str, dict] = {}
    if pred_path.exists():
        with open(pred_path, encoding="utf-8") as f:
            predictions = json.load(f)
        print(f"Resuming: {len(predictions)} existing predictions loaded")

    # Run inference
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from jfinqa._metrics import numerical_match
    from jfinqa.models import QAPair, Question, Subtask, Table

    errors = 0
    for i, q in enumerate(raw):
        qid = q["id"]
        if qid in predictions:
            continue

        # Build context
        question_obj = Question(
            id=qid,
            subtask=Subtask(q["subtask"]),
            pre_text=q["pre_text"],
            post_text=q["post_text"],
            table=Table(headers=q["table"]["headers"], rows=q["table"]["rows"]),
            qa=QAPair(
                question=q["qa"]["question"],
                program=q["qa"]["program"],
                answer=q["qa"]["answer"],
                gold_evidence=q["qa"]["gold_evidence"],
            ),
        )
        context = question_obj.format_context()
        gold = q["qa"]["answer"]

        try:
            raw_response = call_fn(args.model, q["qa"]["question"], context)
            predicted = _extract_answer(raw_response)
            correct = numerical_match(predicted, gold)

            predictions[qid] = {
                "id": qid,
                "subtask": q["subtask"],
                "question": q["qa"]["question"],
                "gold": gold,
                "predicted": predicted,
                "raw_response": raw_response,
                "correct": correct,
            }

            status = "OK" if correct else "NG"
            print(
                f"[{i+1}/{len(raw)}] {status} {qid}: "
                f"pred={predicted!r} gold={gold!r}"
            )

        except Exception as e:
            errors += 1
            print(f"[{i+1}/{len(raw)}] ERROR {qid}: {e}")
            if errors > 10:
                print("Too many errors, stopping.")
                break
            time.sleep(2)
            continue

        # Save periodically
        if (i + 1) % 20 == 0:
            with open(pred_path, "w", encoding="utf-8") as f:
                json.dump(predictions, f, ensure_ascii=False, indent=2)

        # Rate limit
        time.sleep(0.3)

    # Final save
    with open(pred_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)

    # Compute results
    total = len(predictions)
    correct_count = sum(1 for p in predictions.values() if p["correct"])
    accuracy = correct_count / total if total > 0 else 0.0

    from collections import Counter

    by_subtask: dict[str, dict] = {}
    subtask_counts: dict[str, Counter] = {}
    for p in predictions.values():
        st = p["subtask"]
        if st not in subtask_counts:
            subtask_counts[st] = Counter()
        subtask_counts[st]["total"] += 1
        if p["correct"]:
            subtask_counts[st]["correct"] += 1

    for st, counts in sorted(subtask_counts.items()):
        by_subtask[st] = {
            "accuracy": counts["correct"] / counts["total"],
            "correct": counts["correct"],
            "total": counts["total"],
        }

    results = {
        "model": args.model,
        "overall_accuracy": accuracy,
        "correct": correct_count,
        "total": total,
        "by_subtask": by_subtask,
    }

    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Print summary
    print()
    print("=" * 50)
    print(f"Model: {args.model}")
    print(f"Overall: {accuracy:.1%} ({correct_count}/{total})")
    for st, r in sorted(by_subtask.items()):
        print(f"  {st}: {r['accuracy']:.1%} ({r['correct']}/{r['total']})")
    print(f"\nPredictions: {pred_path}")
    print(f"Results: {result_path}")


if __name__ == "__main__":
    main()
