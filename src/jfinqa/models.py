"""Domain models for the jfinqa benchmark.

All public models use Pydantic v2 for validation and serialization.
Data formats are compatible with FinQA (Chen et al., 2021) for
cross-benchmark comparability.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class Subtask(str, Enum):
    """Benchmark subtask categories."""

    NUMERICAL_REASONING = "numerical_reasoning"
    CONSISTENCY_CHECKING = "consistency_checking"
    TEMPORAL_REASONING = "temporal_reasoning"

    @classmethod
    def all(cls) -> list[Subtask]:
        """Return all subtask values."""
        return list(cls)


# ---------------------------------------------------------------------------
# Table
# ---------------------------------------------------------------------------


class Table(BaseModel):
    """A financial data table extracted from a disclosure document.

    Stores tabular data in a structured format with separate headers
    and rows. Provides conversion to/from FinQA's list-of-lists format.

    Attributes:
        headers: Column header labels.
        rows: Data rows, each a list of cell values (strings).
    """

    headers: list[str]
    rows: list[list[str]]

    model_config = {"frozen": True}

    def to_finqa_format(self) -> list[list[str]]:
        """Convert to FinQA's list-of-lists format.

        FinQA represents tables as ``[headers, row1, row2, ...]``.

        >>> t = Table(headers=["", "2024"], rows=[["Revenue", "100"]])
        >>> t.to_finqa_format()
        [['', '2024'], ['Revenue', '100']]
        """
        return [self.headers, *self.rows]

    @classmethod
    def from_finqa_format(cls, data: list[list[str]]) -> Table:
        """Parse from FinQA's list-of-lists format.

        >>> Table.from_finqa_format([["", "2024"], ["Revenue", "100"]])
        Table(headers=['', '2024'], rows=[['Revenue', '100']])
        """
        if not data:
            return cls(headers=[], rows=[])
        return cls(headers=data[0], rows=data[1:])

    def to_markdown(self) -> str:
        """Render as a Markdown table for LLM prompts.

        >>> t = Table(headers=["Item", "2024"], rows=[["Revenue", "100"]])
        >>> print(t.to_markdown())
        | Item | 2024 |
        | --- | --- |
        | Revenue | 100 |
        """
        if not self.headers:
            return ""
        header_line = "| " + " | ".join(self.headers) + " |"
        sep_line = "| " + " | ".join("---" for _ in self.headers) + " |"
        row_lines = ["| " + " | ".join(row) + " |" for row in self.rows]
        return "\n".join([header_line, sep_line, *row_lines])

    @property
    def num_rows(self) -> int:
        """Number of data rows (excluding header)."""
        return len(self.rows)

    @property
    def num_cols(self) -> int:
        """Number of columns."""
        return len(self.headers)


# ---------------------------------------------------------------------------
# QA Pair
# ---------------------------------------------------------------------------


class QAPair(BaseModel):
    """A question-answer pair with optional reasoning program.

    The ``program`` field stores a list of DSL operations that produce
    the answer, following the FinQA program format. Each step is a
    string like ``"subtract(100, 90)"`` or ``"divide(#0, 90)"``,
    where ``#N`` refers to the result of step N.

    Attributes:
        question: The natural-language question.
        program: Sequence of DSL operations producing the answer.
        answer: The gold-standard answer string.
        gold_evidence: Indices of table rows used as evidence.
    """

    question: str
    program: list[str] = Field(default_factory=list)
    answer: str
    gold_evidence: list[int] = Field(default_factory=list)

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Question (main benchmark item)
# ---------------------------------------------------------------------------


class Question(BaseModel):
    """A single benchmark question with context and metadata.

    This is the primary data unit of jfinqa. Each question contains:
    - Textual context (paragraphs before/after a financial table)
    - A structured table
    - A question-answer pair with optional reasoning program
    - Metadata linking back to the source EDINET filing

    The format is compatible with FinQA (Chen et al., 2021) via
    :meth:`to_finqa_format` and :meth:`from_finqa_format`.

    Attributes:
        id: Unique question identifier (e.g. ``"nr_001"``).
        subtask: Which benchmark subtask this belongs to.
        pre_text: Paragraphs preceding the table.
        post_text: Paragraphs following the table.
        table: The financial data table.
        qa: The question-answer pair.
        edinet_code: Source company's EDINET code, if applicable.
        filing_year: Source fiscal year, if applicable.
        accounting_standard: Accounting standard (J-GAAP/IFRS/US-GAAP).
        source_doc_id: EDINET document ID for provenance.
    """

    id: str
    subtask: Subtask
    pre_text: list[str] = Field(default_factory=list)
    post_text: list[str] = Field(default_factory=list)
    table: Table
    qa: QAPair
    edinet_code: str | None = None
    filing_year: str | None = None
    accounting_standard: str | None = None
    source_doc_id: str | None = None

    model_config = {"frozen": True}

    def format_context(self) -> str:
        """Format the full context for LLM input.

        Combines pre_text, table (as Markdown), and post_text into
        a single string suitable for prompting.
        """
        parts: list[str] = []
        if self.pre_text:
            parts.append("\n".join(self.pre_text))
        if self.table.headers:
            parts.append(self.table.to_markdown())
        if self.post_text:
            parts.append("\n".join(self.post_text))
        return "\n\n".join(parts)

    def to_finqa_format(self) -> dict[str, Any]:
        """Export to FinQA-compatible JSON dict.

        Returns a dict matching the FinQA dataset schema, enabling
        direct use with existing FinQA evaluation scripts.
        """
        return {
            "id": self.id,
            "pre_text": self.pre_text,
            "post_text": self.post_text,
            "table": self.table.to_finqa_format(),
            "qa": {
                "question": self.qa.question,
                "program": self.qa.program,
                "answer": self.qa.answer,
                "gold_evidence": self.qa.gold_evidence,
            },
        }

    @classmethod
    def from_finqa_format(
        cls,
        data: dict[str, Any],
        *,
        subtask: Subtask = Subtask.NUMERICAL_REASONING,
    ) -> Question:
        """Import from a FinQA-format JSON dict.

        Args:
            data: A FinQA-format question dict.
            subtask: Subtask label to assign.
        """
        qa_data = data.get("qa", {})
        return cls(
            id=data.get("id", ""),
            subtask=subtask,
            pre_text=data.get("pre_text", []),
            post_text=data.get("post_text", []),
            table=Table.from_finqa_format(data.get("table", [])),
            qa=QAPair(
                question=qa_data.get("question", ""),
                program=qa_data.get("program", []),
                answer=qa_data.get("answer", ""),
                gold_evidence=qa_data.get("gold_evidence", []),
            ),
            edinet_code=data.get("edinet_code"),
            filing_year=data.get("filing_year"),
            accounting_standard=data.get("accounting_standard"),
            source_doc_id=data.get("source_doc_id"),
        )


# ---------------------------------------------------------------------------
# Evaluation Results
# ---------------------------------------------------------------------------


class QuestionResult(BaseModel):
    """Evaluation result for a single question.

    Attributes:
        question_id: The question's unique identifier.
        subtask: Which subtask the question belongs to.
        predicted: The model's predicted answer.
        gold: The gold-standard answer.
        correct: Whether the prediction is correct.
    """

    question_id: str
    subtask: Subtask
    predicted: str
    gold: str
    correct: bool


class SubtaskResult(BaseModel):
    """Aggregate results for a single subtask.

    Attributes:
        accuracy: Fraction of correct predictions.
        total: Total number of questions.
        correct: Number of correct predictions.
    """

    accuracy: float
    total: int
    correct: int


class BenchmarkResult(BaseModel):
    """Aggregate evaluation results across the full benchmark.

    Attributes:
        accuracy: Overall accuracy.
        total: Total number of questions evaluated.
        correct: Total number of correct predictions.
        by_subtask: Per-subtask breakdown.
        results: Detailed per-question results.
    """

    accuracy: float
    total: int
    correct: int
    by_subtask: dict[str, SubtaskResult]
    results: list[QuestionResult]

    def summary(self) -> str:
        """Return a human-readable summary string."""
        lines = [
            "jfinqa Benchmark Results",
            "=" * 40,
            f"Overall: {self.accuracy:.1%} ({self.correct}/{self.total})",
            "",
        ]
        for name, sub in sorted(self.by_subtask.items()):
            lines.append(f"  {name}: {sub.accuracy:.1%} ({sub.correct}/{sub.total})")
        return "\n".join(lines)
