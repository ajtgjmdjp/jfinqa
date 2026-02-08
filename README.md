# jfinqa

Japanese Financial Numerical Reasoning QA Benchmark.

[![PyPI](https://img.shields.io/pypi/v/jfinqa)](https://pypi.org/project/jfinqa/)
[![Python](https://img.shields.io/pypi/pyversions/jfinqa)](https://pypi.org/project/jfinqa/)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

## What is this?

**jfinqa** is a benchmark for evaluating LLMs on Japanese financial question answering. Unlike existing benchmarks that focus on classification or simple lookup, jfinqa requires **cross-referencing text and tables** to perform numerical reasoning over real Japanese corporate disclosures.

### Three Subtasks

| Subtask | Description | Example |
|---------|-------------|---------|
| **Numerical Reasoning** | Calculate financial metrics from table data | "2024年3月期の売上高成長率は何%か？" |
| **Consistency Checking** | Verify internal consistency of reported figures | "資産合計は流動資産と固定資産の合計と一致するか？" |
| **Temporal Reasoning** | Analyze trends and changes across periods | "売上高が最も低かったのはどの年度か？" |

### Dataset Statistics

| | Total | Numerical Reasoning | Consistency Checking | Temporal Reasoning |
|---|---|---|---|---|
| **Questions** | 927 | 550 | 200 | 177 |
| **Companies** | 68 | — | — | — |
| **Accounting Standards** | J-GAAP 57%, IFRS 39%, US-GAAP 4% | — | — | — |

### Baseline Results

| Model | Overall | Numerical Reasoning | Consistency Checking | Temporal Reasoning |
|-------|---------|--------------------|--------------------|-------------------|
| GPT-4o | **84.9%** | 76.7% | **94.0%** | **100.0%** |
| GPT-4o-mini | 74.9% | **83.5%** | 88.0% | 33.3% |
| Gemini 2.0 Flash | 74.5% | 75.5% | 82.5% | 62.7% |

*927 questions, zero-shot, temperature=0. Evaluation uses numerical matching with 1% tolerance.*

### Error Analysis

Systematic error analysis across 3 models revealed both benchmark design issues and genuine LLM failure patterns.

**Evaluation methodology fix**: An initial version reported GPT-4o-mini (70.2%) outperforming GPT-4o (63.7%). This counterintuitive result was caused by inconsistent unit handling in the evaluation: (1) 23 gold answers included redundant "百万円" suffixes that models correctly omitted, and (2) GPT-4o appended "百万円" to 43 consistency-checking answers where the gold expected bare numbers. After standardizing gold answers and treating compound financial units (百万円, 億円) as unit labels rather than multipliers, GPT-4o correctly ranks first at 79.8%.

**Genuine error patterns** (not caused by formatting):

| Error Pattern | GPT-4o | GPT-4o-mini | Gemini 2.0 Flash |
|---|---|---|---|
| Equity ratio: uses 株主資本 instead of 純資産合計 | 23/24 | 16/24 | 24/24 |
| Fixed asset ratio: decomposes into 4 sub-categories | 25/29 | 1/29 | 29/29 |
| Temporal reasoning: answers はい instead of 増収/減収 | 0/75 | 49/75 | 0/75 |
| BS rounding: ±0.1 from XBRL rounding causes false negative | 2 | 2 | 2 |

Key findings:
- **J-GAAP balance sheet structure is the largest source of genuine errors.** Models confuse 純資産合計 (net assets, including non-controlling interests) with 株主資本 (shareholders' equity), and decompose 総資産 into 4 sub-categories instead of the standard 2-category (流動資産+固定資産) structure. GPT-4o-mini is notably better at this than GPT-4o and Gemini.
- **GPT-4o-mini has a systematic prompt compliance issue in temporal reasoning.** It answers "はい" (yes) to questions like "増収か減収か？" despite correctly analyzing the direction in its reasoning chain. This is a pure instruction-following failure, not a reasoning error.
- **GPT-4o and Gemini are highly correlated in failures** on ratio calculations (43 shared errors), while GPT-4o-mini uses a different (often correct) approach to total assets calculation.

### Key Features

- **FinQA-compatible**: Same data format as [FinQA](https://github.com/czyssrs/FinQA) for cross-benchmark comparison
- **Japan-specific**: Handles J-GAAP, IFRS, US-GAAP, and Japanese number formats (百万円, 億円, △)
- **Dual evaluation**: Exact match and numerical match with tolerance
- **lm-evaluation-harness integration**: Ready-to-use YAML task configs
- **Source provenance**: Every question links back to its EDINET filing

## Quick Start

### Installation

```bash
pip install jfinqa
# or
uv add jfinqa
```

### Evaluate Your Model

```python
from jfinqa import load_dataset, evaluate

# Load benchmark questions
questions = load_dataset("numerical_reasoning")

# Provide predictions
predictions = {"nr_001": "25.0%", "nr_002": "16.0%"}
result = evaluate(questions, predictions=predictions)
print(result.summary())
```

### Or Use a Model Function

```python
from jfinqa import load_dataset, evaluate

questions = load_dataset()

def my_model(question: str, context: str) -> str:
    # Your model inference here
    return "42.5%"

result = evaluate(questions, model_fn=my_model)
print(result.summary())
```

## CLI

```bash
# Inspect dataset questions
jfinqa inspect -s numerical_reasoning -n 5

# Evaluate predictions file
jfinqa evaluate -p predictions.json

# Evaluate with local data
jfinqa evaluate -p predictions.json -d local_data.json -s numerical_reasoning
```

## lm-evaluation-harness

```bash
lm_eval --model openai \
    --model_args model=gpt-4o \
    --tasks jfinqa_numerical,jfinqa_consistency,jfinqa_temporal \
    --include_path /path/to/jfinqa/lm_eval_tasks/
```

## Data Format

Each question follows the FinQA schema with additional metadata:

```json
{
  "id": "nr_001",
  "subtask": "numerical_reasoning",
  "pre_text": ["以下はA社の連結損益計算書の抜粋である。"],
  "post_text": ["当期は前期比で増収増益となった。"],
  "table": {
    "headers": ["", "2024年3月期", "2023年3月期"],
    "rows": [
      ["売上高", "1,500,000", "1,200,000"],
      ["営業利益", "200,000", "150,000"]
    ]
  },
  "qa": {
    "question": "2024年3月期の売上高成長率は何%か？",
    "program": ["subtract(1500000, 1200000)", "divide(#0, 1200000)", "multiply(#1, 100)"],
    "answer": "25.0%",
    "gold_evidence": [0]
  },
  "edinet_code": "E00001",
  "filing_year": "2024",
  "accounting_standard": "J-GAAP"
}
```

## Japanese Number Handling

jfinqa correctly normalizes Japanese financial number formats:

| Input | Extracted Value | Notes |
|-------|----------------|-------|
| `△1,000` | -1,000 | Triangle negative marker |
| `１２，３４５` | 12,345 | Fullwidth digits + comma removal |
| `24,956百万円` | 24,956 | Compound financial units treated as labels |
| `50億` | 5,000,000,000 | Bare kanji multiplier applied |
| `42.5%` | 42.5 | Percentage |

## Development

```bash
git clone https://github.com/ajtgjmdjp/jfinqa
cd jfinqa
uv sync --dev --extra dev
uv run pytest -v
uv run ruff check .
uv run mypy src/
```

## Data Attribution

Source financial data is obtained from [EDINET](https://disclosure.edinet-fsa.go.jp/)
(Electronic Disclosure for Investors' NETwork), operated by the
Financial Services Agency of Japan (金融庁).
EDINET data is provided under the [Public Data License 1.0](https://www.digital.go.jp/resources/open_data/).

The data format is compatible with [FinQA](https://github.com/czyssrs/FinQA) (Chen et al., 2021).

## Related Projects

- [FinQA](https://github.com/czyssrs/FinQA) — English financial QA benchmark (Chen et al., 2021)
- [TAT-QA](https://github.com/NExTplusplus/TAT-QA) — Tabular and textual QA
- [edinet-mcp](https://github.com/ajtgjmdjp/edinet-mcp) — EDINET XBRL parser (companion project)
- [EDINET-Bench](https://github.com/SakanaAI/EDINET-Bench) — Sakana AI's financial classification benchmark

## License

Apache-2.0. See [NOTICE](NOTICE) for third-party attributions.
