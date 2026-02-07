"""Evaluation engine for the jfinqa benchmark.

The main entry point is :func:`evaluate`, which accepts either
pre-computed predictions or a callable model function.

Examples::

    from jfinqa import load_dataset, evaluate

    questions = load_dataset("numerical_reasoning")

    # With pre-computed predictions
    preds = {"nr_001": "42.5%", "nr_002": "1,234百万円"}
    result = evaluate(questions, predictions=preds)

    # With a model function
    def my_model(question: str, context: str) -> str:
        return "42.5%"

    result = evaluate(questions, model_fn=my_model)
    print(result.summary())
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Protocol

from loguru import logger

from jfinqa._metrics import exact_match, numerical_match
from jfinqa.models import (
    BenchmarkResult,
    Question,
    QuestionResult,
    SubtaskResult,
)


class ModelFn(Protocol):
    """Protocol for model callable used in evaluation."""

    def __call__(self, question: str, context: str) -> str: ...


def evaluate(
    questions: list[Question],
    *,
    predictions: dict[str, str] | None = None,
    model_fn: ModelFn | Any | None = None,
    match_mode: str = "numerical",
    numerical_tolerance: float = 0.01,
) -> BenchmarkResult:
    """Evaluate model predictions against gold answers.

    Exactly one of ``predictions`` or ``model_fn`` must be provided.

    Args:
        questions: List of benchmark questions to evaluate.
        predictions: Mapping of question ID to predicted answer string.
        model_fn: A callable ``(question, context) -> answer`` that
            generates predictions on the fly.
        match_mode: Comparison strategy: ``"exact"`` for string match,
            ``"numerical"`` for numeric tolerance (default).
        numerical_tolerance: Relative tolerance for numerical matching
            (default: 1%).

    Returns:
        :class:`BenchmarkResult` with overall and per-subtask metrics.

    Raises:
        ValueError: If neither or both of ``predictions`` and
            ``model_fn`` are provided.
    """
    if predictions is None and model_fn is None:
        msg = "Provide either 'predictions' or 'model_fn'"
        raise ValueError(msg)
    if predictions is not None and model_fn is not None:
        msg = "Provide only one of 'predictions' or 'model_fn'"
        raise ValueError(msg)

    match_fn = _get_match_fn(match_mode, numerical_tolerance)

    results: list[QuestionResult] = []
    for q in questions:
        predicted = _get_prediction(q, predictions, model_fn)
        correct = match_fn(predicted, q.qa.answer)
        results.append(
            QuestionResult(
                question_id=q.id,
                subtask=q.subtask,
                predicted=predicted,
                gold=q.qa.answer,
                correct=correct,
            )
        )

    return _aggregate(results)


def _get_prediction(
    question: Question,
    predictions: dict[str, str] | None,
    model_fn: ModelFn | Any | None,
) -> str:
    """Get prediction for a single question."""
    if predictions is not None:
        pred = predictions.get(question.id, "")
        if not pred:
            logger.warning(f"No prediction for {question.id}")
        return pred

    assert model_fn is not None
    context = question.format_context()
    return str(model_fn(question.qa.question, context))


def _get_match_fn(
    mode: str,
    tolerance: float,
) -> Any:
    """Return the appropriate matching function."""
    if mode == "exact":
        return exact_match
    if mode == "numerical":

        def _match(pred: str, gold: str) -> bool:
            return numerical_match(pred, gold, rel_tolerance=tolerance)

        return _match

    msg = f"Unknown match_mode: {mode!r}. Use 'exact' or 'numerical'."
    raise ValueError(msg)


def _aggregate(results: list[QuestionResult]) -> BenchmarkResult:
    """Aggregate per-question results into a BenchmarkResult."""
    total = len(results)
    correct = sum(1 for r in results if r.correct)

    by_subtask: dict[str, list[QuestionResult]] = defaultdict(list)
    for r in results:
        by_subtask[r.subtask.value].append(r)

    subtask_results: dict[str, SubtaskResult] = {}
    for name, sub_results in sorted(by_subtask.items()):
        sub_total = len(sub_results)
        sub_correct = sum(1 for r in sub_results if r.correct)
        subtask_results[name] = SubtaskResult(
            accuracy=sub_correct / sub_total if sub_total > 0 else 0.0,
            total=sub_total,
            correct=sub_correct,
        )

    return BenchmarkResult(
        accuracy=correct / total if total > 0 else 0.0,
        total=total,
        correct=correct,
        by_subtask=subtask_results,
        results=results,
    )
