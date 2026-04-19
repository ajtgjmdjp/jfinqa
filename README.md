# jfinqa

Japanese Financial Numerical Reasoning QA Benchmark.

[![PyPI](https://img.shields.io/pypi/v/jfinqa)](https://pypi.org/project/jfinqa/)
[![Python](https://img.shields.io/pypi/pyversions/jfinqa)](https://pypi.org/project/jfinqa/)
[![CI](https://github.com/ajtgjmdjp/jfinqa/actions/workflows/ci.yml/badge.svg)](https://github.com/ajtgjmdjp/jfinqa/actions/workflows/ci.yml)
[![Downloads](https://img.shields.io/pypi/dm/jfinqa)](https://pypi.org/project/jfinqa/)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Dataset-yellow)](https://huggingface.co/datasets/ajtgjmdjp/jfinqa)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)
[![Leaderboard](https://img.shields.io/badge/Leaderboard-Live-brightgreen)](https://ajtgjmdjp.github.io/jfinqa-leaderboard/)

## What is this?

**jfinqa** is a benchmark for evaluating LLMs on Japanese financial numerical reasoning. Unlike existing benchmarks that focus on classification or simple lookup, jfinqa requires **multi-step arithmetic over financial statement tables** extracted from real Japanese corporate disclosures (EDINET). Questions include DuPont decomposition (6-step), growth rate calculations, and cross-statement ratio analysis.

### Three Subtasks

| Subtask | Description | Example |
|---------|-------------|---------|
| **Numerical Reasoning** | Calculate financial metrics from table data | "2024年3月期の売上高成長率は何%か？" |
| **Consistency Checking** | Verify internal consistency of reported figures | "資産合計は流動資産と固定資産の合計と一致するか？" |
| **Temporal Reasoning** | Analyze trends and changes across periods | "売上高が最も低かったのはどの年度か？" |

### Dataset Statistics

| | Total | Numerical Reasoning | Consistency Checking | Temporal Reasoning |
|---|---|---|---|---|
| **Questions** | 1000 | 550 | 200 | 250 |
| **Companies** | 104 | — | — | — |
| **Accounting Standards** | J-GAAP 65.6%, IFRS 32.3%, US-GAAP 2.1% | — | — | — |
| **Avg. program steps** | 2.58 | 2.84 | 2.00 | 2.54 |
| **Avg. table rows** | 13.3 | — | — | — |
| **Max program steps** | 6 (DuPont) | — | — | — |

### Evaluation Regimes

Baseline runs are reported under two reasoning regimes so that thinking/non-thinking behaviour can be compared on the same prompts:

- **R0** — thinking/reasoning disabled. The model produces a direct answer with no reasoning budget.
- **R1** — native moderate reasoning enabled (provider-default thinking budget). No custom token limit is imposed; we rely on each provider's default "moderate" setting.

All baseline numbers below are zero-shot, temperature=0, and evaluated over the full 1000-question dataset unless otherwise noted. Accuracy uses numerical matching with 1% tolerance on numerical subtasks and exact-match on categorical answers.

### Baseline Results

Full 1000-question run, sorted by overall accuracy:

| Model | Regime | Accuracy | Num | Cons | Temp | Cost (USD) |
|---|---|---:|---:|---:|---:|---:|
| gpt-5.4-mini | R0 | **93.7%** | 89.5 | 97.5 | 100.0 | $0.36 |
| gpt-5.4-mini | R1 | 92.4% | 87.1 | 97.5 | 100.0 | $1.18 |
| gpt-5.4 (frontier) | R1 | 91.9% | 86.5 | 97.5 | 99.2 | $5.83 |
| gpt-5.4 (frontier) | R0 | 90.6% | 83.8 | 97.5 | 100.0 | $1.98 |
| gemini-2.5-pro | R1 | 89.87% (N=977) | 84.0 | 96.5 | 98.24 | $11.77 |
| gemini-2.5-flash | R0 | 89.6% | 82.4 | 96.5 | 100.0 | $0.09 |
| gemini-2.5-flash-lite | R1 | 88.3% | 81.8 | 94.0 | 98.0 | $0.18 |
| gemini-2.5-flash-lite | R0 | 87.6% | 80.4 | 93.0 | 99.2 | $0.05 |
| gemini-2.5-flash | R1 | 87.6% | 83.3 | 98.0 | 88.8 | $0.23 |
| gpt-5.4-nano | R1 | 85.6% | 86.2 | 90.0 | 80.8 | $0.28 |
| gpt-5.4-nano | R0 | 78.7% | 88.0 | 90.0 | 49.2 | $0.07 |

*Num = Numerical Reasoning (n=550), Cons = Consistency Checking (n=200), Temp = Temporal Reasoning (n=250). gemini-2.5-pro R1 was evaluated on 977 of 1000 questions due to provider-side timeouts on 23 items; the remaining columns are over the scored subset.*

**[View full leaderboard →](https://ajtgjmdjp.github.io/jfinqa-leaderboard/)**

### Key Findings

1. **Non-monotonic scaling within the gpt-5.4 family.** `gpt-5.4-mini` R0 (93.7%) outperforms the frontier `gpt-5.4` under both regimes (91.9% R1 / 90.6% R0) at roughly one-sixteenth of the R1 cost. Parameter count is not a reliable predictor of jfinqa accuracy among current frontier models.
2. **Thinking effect is strongly model-dependent.** Turning on native reasoning (R0 → R1) moves accuracy by +6.9 pt for `gpt-5.4-nano`, +1.3 pt for `gpt-5.4` (frontier), -1.3 pt for `gpt-5.4-mini`, and -2.0 pt for `gemini-2.5-flash`. Thinking helps weaker models but can hurt already-tuned ones — regime must be tuned per model, not applied blindly.
3. **Temporal reasoning saturates in the top 7 models** (≥98% Temp), confirming that format-compliance on 増収/減収-style answers is essentially solved at frontier scale. The earlier TR gap observed on GPT-4o-class models has closed.
4. **Numerical reasoning is now the discriminating subtask.** Num scores span 80.4% – 89.5% across top models while Cons and Temp are near-ceiling, so further differentiation between frontier systems on jfinqa comes almost entirely from multi-step arithmetic (growth rates, DuPont, cross-statement ratios), not from format-following.

Additional qualitative observations, including J-GAAP balance sheet confusion (純資産合計 vs. 株主資本) and the hardness of 6-step DuPont items, continue to hold from the pre-audit error analysis and are documented in the leaderboard notes.

### Pre-audit baselines (deprecated)

The numbers below were measured on the **pre-audit `v1.0-legacy-2026-02` dataset** before the 2026-04 EDINET-mapping fixes and the expansion to 104 companies. They are retained for historical comparison only and should **not** be compared directly to the current table — the underlying questions, company mix, and accounting-standard distribution have changed.

| Model | Overall | Numerical Reasoning | Consistency Checking | Temporal Reasoning |
|-------|---------|--------------------|--------------------|-------------------|
| GPT-4o | 87.0% | 80.2% | 90.5% | 99.2% |
| Gemini 2.0 Flash | 80.4% | 86.2% | 83.5% | 65.2% |
| GPT-4o-mini | 67.7% | 79.3% | 83.5% | 29.6% |
| Qwen2.5-3B-Instruct | 39.6% | 46.4% | 51.0% | 15.6% |

*Measured on pre-audit v1.0-legacy-2026-02. Zero-shot, temperature=0, numerical matching with 1% tolerance. Qwen2.5-3B-Instruct run locally with MLX (4-bit quantization).*

### Key Features

- **FinQA-compatible**: Same data format as [FinQA](https://github.com/czyssrs/FinQA) for cross-benchmark comparison
- **Japan-specific**: Handles J-GAAP, IFRS, US-GAAP, and Japanese number formats (百万円, 億円, △)
- **Dual evaluation**: Exact match and numerical match with tolerance
- **Multi-harness integration**: Merged into lm-evaluation-harness (PR #3570) and llm-jp-eval (PR #230)
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

jfinqa is merged into lm-eval via
[PR #3570](https://github.com/EleutherAI/lm-evaluation-harness/pull/3570)
(2026-03-18). With a current lm-eval install you can run the task directly:

```bash
lm-eval run --model openai-completions \
    --model_args model=gpt-4o \
    --tasks jfinqa \
    --num_fewshot 0
```

This repository also ships a commit-pinned mirror of the task in
[`lm_eval_tasks/`](lm_eval_tasks/README.md) for reproducibility. To use
the in-repo copy instead of whatever ships with lm-eval, clone the repo
and pass `--include_path`:

```bash
lm-eval run --model openai-completions \
    --model_args model=gpt-4o \
    --tasks jfinqa \
    --num_fewshot 0 \
    --include_path lm_eval_tasks/
```

The mirror is not packaged into the published wheel; it is only
available from a git checkout. Run
[`scripts/sync_lm_eval.py`](scripts/sync_lm_eval.py) to diff the mirror
against upstream.

## llm-jp-eval

jfinqa is also merged into llm-jp-eval via
[PR #230](https://github.com/llm-jp/llm-jp-eval/pull/230)
(2026-03-04, commit
[`f1604e77`](https://github.com/llm-jp/llm-jp-eval/commit/f1604e77df638d43a8caf097680703fc85b0fa87)).
Unlike the lm-evaluation-harness integration, **this repository does
not mirror the llm-jp-eval task**. The upstream implementation at
[`src/llm_jp_eval/jaster/jfinqa.py`](https://github.com/llm-jp/llm-jp-eval/blob/f1604e77df638d43a8caf097680703fc85b0fa87/src/llm_jp_eval/jaster/jfinqa.py)
(pinned at the PR #230 merge commit) is the single source of truth.

### Why no mirror here

llm-jp-eval wraps jfinqa inside its own `BaseDatasetProcessor` pipeline,
with a Japanese prompt (`質問：`) and a LaTeX-boxed answer format
(`$\boxed{...}$`) scored by the internal `mathematical_equivalence`
metric. None of that scoring logic depends on this repository's
`jfinqa._metrics`, so there is nothing to keep in sync — mirroring it
locally would only add maintenance cost.

### Harness comparison

The three harnesses therefore evaluate the same 1000 questions but
report **different numbers**. Treat them as separate protocols:

| Harness          | Source of truth              | Prompt style                   | Scoring                             | Local mirror?  |
|------------------|------------------------------|--------------------------------|-------------------------------------|----------------|
| `jfinqa` package | this repo                    | caller-supplied                | `jfinqa._metrics`                   | canonical      |
| lm-evaluation-harness | upstream + pinned mirror | `Question: ... Answer:` (EN) | `exact_match` + `numerical_match`   | [`lm_eval_tasks/`](lm_eval_tasks/README.md) |
| llm-jp-eval      | upstream only                | `質問：... $\boxed{...}$` (JP)  | `mathematical_equivalence`          | none           |

### Running llm-jp-eval

Install llm-jp-eval and the jfinqa task will be available under the
name `jfinqa`; the dataset is fetched from Hugging Face automatically.
See the [llm-jp-eval
documentation](https://github.com/llm-jp/llm-jp-eval) for invocation
details. Pin the llm-jp-eval commit in experiment configs if you need
byte-level reproducibility.

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

## Citation

If you use jfinqa in your research, please cite it as follows:

```bibtex
@dataset{jfinqa2025,
  title={jfinqa: Japanese Financial Numerical Reasoning QA Benchmark},
  author={ajtgjmdjp},
  year={2025},
  url={https://github.com/ajtgjmdjp/jfinqa},
  license={Apache-2.0}
}
```

## License

Apache-2.0. See [NOTICE](NOTICE) for third-party attributions.
