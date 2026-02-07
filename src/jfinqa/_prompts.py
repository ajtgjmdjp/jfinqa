"""Prompt templates for LLM evaluation.

Provides standardized prompts for each subtask to ensure consistent
evaluation across different models.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a financial analyst answering questions about Japanese "
    "corporate disclosures. Answer with the exact value requested. "
    "If a percentage is asked, include the % sign. "
    "If a monetary value is asked, include the unit."
)

# ---------------------------------------------------------------------------
# Per-subtask prompts
# ---------------------------------------------------------------------------

NUMERICAL_REASONING_PROMPT = """\
Read the following financial data and answer the question.
Show your calculation steps, then provide the final answer on the last line
in the format "Answer: <value>".

{context}

Question: {question}"""

CONSISTENCY_CHECKING_PROMPT = """\
Read the following financial data and check whether the stated figures \
are internally consistent.

{context}

Question: {question}

Answer with one of:
- "Consistent" if the figures are internally consistent
- "Inconsistent: <explanation>" if there is a discrepancy

Answer:"""

TEMPORAL_REASONING_PROMPT = """\
Read the following multi-period financial data and answer the question \
about trends or changes over time.

{context}

Question: {question}

Answer:"""

# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------

PROMPTS: dict[str, str] = {
    "numerical_reasoning": NUMERICAL_REASONING_PROMPT,
    "consistency_checking": CONSISTENCY_CHECKING_PROMPT,
    "temporal_reasoning": TEMPORAL_REASONING_PROMPT,
}


def format_prompt(
    subtask: str,
    question: str,
    context: str,
) -> str:
    """Format a prompt for the given subtask.

    Args:
        subtask: Subtask name (e.g. ``"numerical_reasoning"``).
        question: The question text.
        context: The formatted context (pre_text + table + post_text).

    Returns:
        The formatted prompt string.
    """
    template = PROMPTS.get(subtask, NUMERICAL_REASONING_PROMPT)
    return template.format(question=question, context=context)
