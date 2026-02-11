"""jfinqa: Japanese Financial Numerical Reasoning QA Benchmark.

Quick start::

    from jfinqa import load_dataset, evaluate

    questions = load_dataset("numerical_reasoning")
    predictions = {"nr_001": "42.5%"}
    result = evaluate(questions, predictions=predictions)
    print(result.summary())
"""

from jfinqa.dataset import load_dataset, load_from_file
from jfinqa.evaluate import evaluate
from jfinqa.models import (
    BenchmarkResult,
    QAPair,
    Question,
    QuestionResult,
    Subtask,
    SubtaskResult,
    Table,
)

__all__ = [
    "BenchmarkResult",
    "QAPair",
    "Question",
    "QuestionResult",
    "Subtask",
    "SubtaskResult",
    "Table",
    "evaluate",
    "load_dataset",
    "load_from_file",
]

__version__ = "0.3.0"
