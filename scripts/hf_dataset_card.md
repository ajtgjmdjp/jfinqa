---
license: apache-2.0
language:
- ja
tags:
- benchmark
- financial
- question-answering
- numerical-reasoning
- japanese
- edinet
pretty_name: "jfinqa: Japanese Financial QA Benchmark"
size_categories:
- n<1K
task_categories:
- question-answering
- table-question-answering
configs:
- config_name: all
  data_files:
  - split: test
    path: all/test-*
- config_name: numerical_reasoning
  data_files:
  - split: test
    path: numerical_reasoning/test-*
- config_name: consistency_checking
  data_files:
  - split: test
    path: consistency_checking/test-*
- config_name: temporal_reasoning
  data_files:
  - split: test
    path: temporal_reasoning/test-*
dataset_info:
- config_name: all
  features:
  - name: id
    dtype: string
  - name: subtask
    dtype: string
  - name: company_name
    dtype: string
  - name: edinet_code
    dtype: string
  - name: source_doc_id
    dtype: string
  - name: filing_year
    dtype: string
  - name: accounting_standard
    dtype: string
  - name: scale
    dtype: string
  - name: pre_text
    sequence: string
  - name: post_text
    sequence: string
  - name: table_headers
    sequence: string
  - name: table_rows
    sequence:
      sequence: string
  - name: question
    dtype: string
  - name: answer
    dtype: string
  - name: program
    sequence: string
  - name: gold_evidence
    sequence: int64
  splits:
  - name: test
    num_examples: 1000
---

# jfinqa: Japanese Financial Numerical Reasoning QA Benchmark

**jfinqa** is a benchmark for evaluating LLMs on Japanese financial question answering that requires **numerical reasoning over real corporate disclosures**.

Unlike existing Japanese financial benchmarks that focus on classification or simple lookup, jfinqa requires models to cross-reference text and tables to perform multi-step calculations.

## Dataset Summary

| | Count |
|---|---|
| Total questions | 1000 |
| Companies | 68 |
| Accounting standards | J-GAAP (582), IFRS (377), US-GAAP (41) |
| Avg. program steps | 2.59 |
| Avg. table rows | 13.3 |
| Max program steps | 6 (DuPont decomposition) |

### Subtasks

| Config | Description | Count |
|--------|-------------|-------|
| `numerical_reasoning` | Calculate financial metrics from table data | 550 |
| `consistency_checking` | Verify internal consistency of reported figures | 200 |
| `temporal_reasoning` | Analyze trends and changes across periods | 250 |

## Usage

```python
from datasets import load_dataset

# Load all questions
ds = load_dataset("ajtgjmdjp/jfinqa", "all", split="test")

# Load a specific subtask
ds_nr = load_dataset("ajtgjmdjp/jfinqa", "numerical_reasoning", split="test")
```

### With the jfinqa library

```python
from jfinqa import load_dataset, evaluate

questions = load_dataset("numerical_reasoning")
result = evaluate(questions, predictions={"nr_001": "25.0%"})
print(result.summary())
```

Install: `pip install jfinqa`

## Data Format

Each example contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique identifier (e.g., `nr_001`, `cc_015`, `tr_042`) |
| `subtask` | string | Task category |
| `company_name` | string | Company name in Japanese |
| `edinet_code` | string | EDINET company code |
| `source_doc_id` | string | Source document ID for provenance |
| `filing_year` | string | Fiscal year |
| `accounting_standard` | string | J-GAAP, IFRS, or US-GAAP |
| `scale` | string | Number unit (百万円, 億円, etc.) |
| `pre_text` | list[string] | Context paragraphs before the table |
| `post_text` | list[string] | Context paragraphs after the table |
| `table_headers` | list[string] | Table column headers |
| `table_rows` | list[list[string]] | Table data rows |
| `question` | string | Question in Japanese |
| `answer` | string | Gold answer |
| `program` | list[string] | FinQA-compatible DSL program |
| `gold_evidence` | list[int] | Indices of relevant table rows |

The data format is compatible with [FinQA](https://github.com/czyssrs/FinQA) (Chen et al., 2021).

## Example

```json
{
  "id": "nr_001",
  "subtask": "numerical_reasoning",
  "company_name": "味の素",
  "question": "味の素の2024年3月期の売上高は前期比で何%増減したか。",
  "answer": "-23.8%",
  "program": ["subtract(126253.0, 165580.0)", "divide(#0, 165580.0)", "multiply(#1, 100)"],
  "table_headers": ["", "2024年3月期", "2023年3月期"],
  "table_rows": [["売上高", "126,253", "165,580"], ["営業利益", "3,557", "△1,191"]]
}
```

## Japanese-Specific Features

- **Accounting standards**: Handles J-GAAP (経常利益), IFRS, and US-GAAP differences
- **Number formats**: △ for negative, 百万円/億円 units, full-width digits
- **Japanese financial terminology**: 売上高, 営業利益, 経常利益, etc.

## Data Source

Financial data is obtained from [EDINET](https://disclosure.edinet-fsa.go.jp/) (Electronic Disclosure for Investors' NETwork), operated by the Financial Services Agency of Japan (金融庁). EDINET data is provided under the [Public Data License 1.0](https://www.digital.go.jp/resources/open_data/).

## Citation

```bibtex
@misc{jfinqa2025,
  title={jfinqa: Japanese Financial Numerical Reasoning QA Benchmark},
  author={ajtgjmdjp},
  year={2025},
  url={https://github.com/ajtgjmdjp/jfinqa},
}
```

## Related

- [jfinqa (GitHub)](https://github.com/ajtgjmdjp/jfinqa) — Evaluation library and CLI
- [edinet-mcp](https://github.com/ajtgjmdjp/edinet-mcp) — EDINET XBRL parser (companion project)
- [FinQA](https://github.com/czyssrs/FinQA) — English financial QA benchmark
- [EDINET-Bench](https://github.com/SakanaAI/EDINET-Bench) — Sakana AI's financial classification benchmark

## License

Apache-2.0. See [NOTICE](https://github.com/ajtgjmdjp/jfinqa/blob/main/NOTICE) for third-party attributions.
