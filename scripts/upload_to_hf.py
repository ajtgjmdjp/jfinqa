"""Upload jfinqa dataset to HuggingFace Hub.

Usage:
    uv run python scripts/upload_to_hf.py

Requires:
    - huggingface-cli login (or HF_TOKEN env var)
    - datasets library
"""

from __future__ import annotations

import json
from pathlib import Path

from datasets import Dataset
from huggingface_hub import HfApi

HF_REPO = "ajtgjmdjp/jfinqa"
DATA_PATH = Path(__file__).parent / "data" / "final" / "jfinqa_v1.json"
CARD_PATH = Path(__file__).parent / "hf_dataset_card.md"


def _flatten_question(q: dict) -> dict:
    """Flatten nested table/qa fields for HuggingFace Dataset."""
    return {
        "id": q["id"],
        "subtask": q["subtask"],
        "company_name": q["company_name"],
        "edinet_code": q["edinet_code"],
        "source_doc_id": q["source_doc_id"],
        "filing_year": q["filing_year"],
        "accounting_standard": q["accounting_standard"],
        "scale": q.get("scale", ""),
        "pre_text": q["pre_text"],
        "post_text": q["post_text"],
        # Table — keep as nested dict (HF datasets supports this)
        "table_headers": q["table"]["headers"],
        "table_rows": q["table"]["rows"],
        # QA
        "question": q["qa"]["question"],
        "answer": q["qa"]["answer"],
        "program": q["qa"]["program"],
        "gold_evidence": q["qa"]["gold_evidence"],
    }


def main() -> None:
    with open(DATA_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    print(f"Loaded {len(raw)} questions from {DATA_PATH}")

    # Split by subtask
    by_subtask: dict[str, list[dict]] = {}
    for q in raw:
        st = q["subtask"]
        by_subtask.setdefault(st, []).append(_flatten_question(q))

    # Create DatasetDict with subtask configs
    configs: dict[str, Dataset] = {}
    for subtask_name, questions in sorted(by_subtask.items()):
        ds = Dataset.from_list(questions)
        configs[subtask_name] = ds
        print(f"  {subtask_name}: {len(ds)} questions")

    # Also create "all" config with everything
    all_questions = [_flatten_question(q) for q in raw]
    configs["all"] = Dataset.from_list(all_questions)
    print(f"  all: {len(all_questions)} questions")

    # Push each config as a separate dataset split
    for config_name, ds in configs.items():
        print(f"\nUploading config '{config_name}'...")
        ds.push_to_hub(
            HF_REPO,
            config_name=config_name,
            split="test",
            private=False,
        )
        print(f"  Done: {config_name}")

    # Upload dataset card (README.md)
    if CARD_PATH.exists():
        print("\nUploading dataset card...")
        api = HfApi()
        api.upload_file(
            path_or_fileobj=str(CARD_PATH),
            path_in_repo="README.md",
            repo_id=HF_REPO,
            repo_type="dataset",
        )
        print("  Done: README.md")

    print(f"\nDataset published at: https://huggingface.co/datasets/{HF_REPO}")


if __name__ == "__main__":
    main()
