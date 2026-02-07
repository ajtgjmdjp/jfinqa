"""Dataset loading for jfinqa.

Provides functions to load benchmark questions from HuggingFace Hub
or local files. The primary entry point is :func:`load_dataset`.

Examples::

    from jfinqa import load_dataset

    # All questions
    questions = load_dataset()

    # Single subtask
    questions = load_dataset("numerical_reasoning")

    # From local file
    questions = load_from_file("path/to/questions.json")
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from jfinqa.models import Question, Subtask

# Default HuggingFace Hub dataset identifier
_DEFAULT_HF_REPO = "ajtgjmdjp/jfinqa"


def load_dataset(
    subtask: str | Subtask | None = None,
    *,
    split: str = "test",
    hf_repo: str = _DEFAULT_HF_REPO,
) -> list[Question]:
    """Load benchmark questions from HuggingFace Hub.

    Args:
        subtask: Filter to a specific subtask (e.g.
            ``"numerical_reasoning"``). If ``None``, loads all.
        split: Dataset split to load (default: ``"test"``).
        hf_repo: HuggingFace repository ID.

    Returns:
        List of :class:`Question` objects.

    Raises:
        ImportError: If ``datasets`` is not installed.
        ValueError: If the dataset or subtask is not found.
    """
    try:
        import datasets as hf_datasets
    except ImportError as e:
        msg = "Install 'datasets' to load from HuggingFace: pip install datasets"
        raise ImportError(msg) from e

    resolved_subtask: Subtask | None = None
    if subtask is not None:
        resolved_subtask = subtask if isinstance(subtask, Subtask) else Subtask(subtask)

    # Load from HuggingFace Hub
    if resolved_subtask is not None:
        config_name = resolved_subtask.value
        logger.info(f"Loading {config_name}/{split} from {hf_repo}")
        ds = hf_datasets.load_dataset(hf_repo, name=config_name, split=split)
        return [_row_to_question(row, resolved_subtask) for row in ds]

    # Load all subtasks
    all_questions: list[Question] = []
    for st in Subtask.all():
        try:
            ds = hf_datasets.load_dataset(hf_repo, name=st.value, split=split)
            questions = [_row_to_question(row, st) for row in ds]
            all_questions.extend(questions)
            logger.info(f"Loaded {len(questions)} from {st.value}/{split}")
        except Exception as e:
            logger.warning(f"Could not load {st.value}: {e}")

    return all_questions


def load_from_file(path: str) -> list[Question]:
    """Load questions from a local JSON or JSONL file.

    Supports two formats:
    - **JSON**: A list of question dicts (``[{...}, {...}]``).
    - **JSONL**: One question dict per line.

    Args:
        path: Path to the file.

    Returns:
        List of :class:`Question` objects.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()

    if text.startswith("["):
        # JSON array
        raw: list[dict[str, Any]] = json.loads(text)
    else:
        # JSONL
        raw = [json.loads(line) for line in text.splitlines() if line.strip()]

    questions = [_dict_to_question(d) for d in raw]
    logger.info(f"Loaded {len(questions)} questions from {path}")
    return questions


def _row_to_question(row: Any, subtask: Subtask) -> Question:
    """Convert a HuggingFace dataset row to a Question."""
    return Question(
        id=row["id"],
        subtask=subtask,
        pre_text=row.get("pre_text", []),
        post_text=row.get("post_text", []),
        table=_parse_table(row.get("table", {})),
        qa=_parse_qa(row.get("qa", {})),
        edinet_code=row.get("edinet_code"),
        filing_year=row.get("filing_year"),
        accounting_standard=row.get("accounting_standard"),
        source_doc_id=row.get("source_doc_id"),
    )


def _dict_to_question(data: dict[str, Any]) -> Question:
    """Convert a raw dict to a Question.

    Supports both jfinqa native format and FinQA format.
    """
    # Detect FinQA format (table is list-of-lists)
    table_raw = data.get("table", {})
    if isinstance(table_raw, list):
        return Question.from_finqa_format(data)

    return Question(
        id=data["id"],
        subtask=Subtask(data.get("subtask", "numerical_reasoning")),
        pre_text=data.get("pre_text", []),
        post_text=data.get("post_text", []),
        table=_parse_table(table_raw),
        qa=_parse_qa(data.get("qa", {})),
        edinet_code=data.get("edinet_code"),
        filing_year=data.get("filing_year"),
        accounting_standard=data.get("accounting_standard"),
        source_doc_id=data.get("source_doc_id"),
    )


def _parse_table(raw: dict[str, Any] | list[Any]) -> Any:
    """Parse table data from various formats."""
    from jfinqa.models import Table

    if isinstance(raw, list):
        return Table.from_finqa_format(raw)
    return Table(
        headers=raw.get("headers", []),
        rows=raw.get("rows", []),
    )


def _parse_qa(raw: dict[str, Any]) -> Any:
    """Parse QA pair from dict."""
    from jfinqa.models import QAPair

    return QAPair(
        question=raw.get("question", ""),
        program=raw.get("program", []),
        answer=raw.get("answer", ""),
        gold_evidence=raw.get("gold_evidence", []),
    )
