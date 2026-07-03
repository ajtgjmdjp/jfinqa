# jfinqa Evaluation Specification

This document is the canonical specification for evaluating models on
jfinqa. It defines exactly what counts as a valid run, how answers are
scored, and how the three supported harnesses relate to each other.
Experiments cited in the jfinqa paper are expected to be reproducible
from this document plus a pinned model snapshot.

Status: **draft** (2026-04-18). Sections marked **TBD** will be
finalized before the paper's experimental section is frozen.

## 1. Dataset

### 1.1 Source of truth

The canonical dataset lives on the Hugging Face Hub at
[`ajtgjmdjp/jfinqa`](https://huggingface.co/datasets/ajtgjmdjp/jfinqa).
Each experiment must pin a dataset revision (a commit hash on the Hub)
and record it alongside the results.

### 1.2 Splits and subtasks

jfinqa ships a single `test` split of 1000 questions, partitioned into
three subtasks by the `subtask` field:

| Subtask                | Count | Code                     |
|------------------------|-------|--------------------------|
| Numerical Reasoning    | 550   | `numerical_reasoning`    |
| Consistency Checking   | 200   | `consistency_checking`   |
| Temporal Reasoning     | 250   | `temporal_reasoning`     |

There is no official validation or train split. Few-shot exemplars, if
used, must be drawn from outside the 1000-question test set and
documented per-experiment.

### 1.3 Schema

Every row follows the FinQA schema with Japan-specific metadata:

| Field               | Type                | Notes                                      |
|---------------------|---------------------|--------------------------------------------|
| `id`                | str                 | e.g., `nr_001`                             |
| `subtask`           | str                 | one of the three subtask codes             |
| `company_name`      | str                 | issuer                                     |
| `edinet_code`       | str                 | EDINET issuer code                         |
| `source_doc_id`     | str                 | EDINET document id                         |
| `filing_year`       | str                 |                                            |
| `accounting_standard` | str               | `J-GAAP` / `IFRS` / `US-GAAP`              |
| `scale`             | str                 | table unit, e.g., `百万円`                  |
| `pre_text`          | list[str]           | paragraphs before the table                |
| `table_headers`     | list[str]           |                                            |
| `table_rows`        | list[list[str]]     |                                            |
| `post_text`         | list[str]           | paragraphs after the table                 |
| `question`          | str                 | Japanese question                          |
| `answer`            | str                 | gold answer as authored                    |
| `program`           | list[str]           | DSL program (optional, for analysis)       |
| `gold_evidence`     | list[int]           | row indices used in the answer             |

## 2. Canonical scoring

The reference implementation is [`src/jfinqa/_metrics.py`](../src/jfinqa/_metrics.py).
Experiments reporting "jfinqa" scores without further qualification
use this module.

### 2.1 Answer normalization

`normalize_answer(s)` applies, in order:

1. Strip leading/trailing whitespace.
2. NFKC unicode normalization (fullwidth → halfwidth digits, etc.).
3. Japanese negative markers: a leading `△` or `▲` becomes `-`.
4. Remove commas placed between digits (`1,234` → `1234`).
5. Remove polite verb endings: trailing `しました` or `した`.
6. Lowercase.

### 2.2 Numeric extraction

`extract_number(s)` first normalizes the string, then:

1. Strips unit suffixes (`百万円`, `千円`, `億円`, `兆円`, `円`, `ドル`,
   `ポイント`, `pt`, `bps`).
2. If a kanji multiplier (`千`, `百万`, `億`, `兆`) remains, it is
   applied to the numeric part that follows.
3. A trailing `%` is stripped and ignored (percentages are compared as
   plain floats; `42.5%` and `42.5` are equivalent).
4. Remaining non-numeric characters are removed.
5. The cleaned string is parsed with `float()`. Failure returns `None`.

### 2.3 Matching functions

- **`exact_match(pred, gold)`** — `True` iff `normalize_answer(pred) ==
  normalize_answer(gold)`.
- **`numerical_match(pred, gold, rel_tolerance=0.01)`** — compares the
  extracted numbers with a default relative tolerance of 1 %. When
  either side fails to parse, falls back to `exact_match`. Zero gold
  values require an exact zero prediction.

The 1 % tolerance is chosen because gold answers are typically rounded
to one decimal place, so a model producing `10.05%` should not be
penalized against a gold of `10.0%`.

### 2.4 Reported metrics

For each subtask and overall:

- `exact_match` — mean of `exact_match(pred, gold)` over the subtask.
- `numerical_match` — mean of `numerical_match(pred, gold)` over the
  subtask (primary metric for ranking).

Confidence intervals, if reported, use bootstrap percentiles with
`n_samples = 1000` over the rows of each subtask.

## 3. Harness matrix

The three supported harnesses evaluate the same 1000 questions but do
not produce comparable numbers. They should be treated as separate
protocols.

| Harness                | Source of truth                 | Prompt style                         | Scoring                                 | Mirror policy                          |
|------------------------|---------------------------------|--------------------------------------|-----------------------------------------|----------------------------------------|
| `jfinqa` package       | this repository                 | caller-supplied                      | `jfinqa._metrics`                       | canonical                              |
| lm-evaluation-harness  | upstream + pinned local mirror  | `Question: {q}\nAnswer:` (English)   | `exact_match` + `numerical_match`       | [`lm_eval_tasks/`](../lm_eval_tasks/README.md) |
| llm-jp-eval            | upstream only                   | `質問：{q}` + `$\boxed{...}$` (JP)   | `mathematical_equivalence` (internal)   | none                                   |

### 3.1 jfinqa package (canonical)

The package exposes `evaluate()` for batch scoring and the primitives
in `jfinqa._metrics` for custom pipelines. Prompts are the caller's
responsibility; the package only scores already-produced predictions.

### 3.2 lm-evaluation-harness

Pinned to upstream PR #3570 merge commit
`eb9253ae7ce21ef2027b94cf5c93c9b44e8aec32`. The in-repo mirror at
`lm_eval_tasks/` is kept byte-identical to that commit via
`scripts/sync_lm_eval.py`. The mirror's scoring logic duplicates
`jfinqa._metrics`; the golden tests in
`tests/test_lm_eval_integration.py` fail if the two drift.

### 3.3 llm-jp-eval

Pinned to upstream PR #230 merge commit `f1604e77df638d43a8caf097680703fc85b0fa87`.
llm-jp-eval wraps jfinqa in its own dataset-processor pipeline and
scores with `mathematical_equivalence`, which is independent of
`jfinqa._metrics`. This repository does not mirror the implementation.

### 3.4 Cross-harness comparisons

Numbers from different harnesses **must not** be placed in the same
table unless the table's caption names all three protocols and their
prompts. Leaderboards may publish separate columns per harness.

## 4. Experiment protocol

### 4.1 Decoding

Unless explicitly reporting otherwise, all main-results experiments
use:

- `temperature = 0.0`
- `top_p = 1.0`
- `max_new_tokens = 256` (sufficient for all observed answers)
- single sample per question (`n = 1`)

For reasoning-model families that do not honor `temperature`, the
model's default decoding is used and documented.

### 4.2 Zero-shot baselines

Main-results tables are zero-shot. Few-shot variants are additional
and must not replace the zero-shot column.

### 4.3 Reproducibility checklist

Every reported run must log:

- jfinqa package version (`pip show jfinqa`)
- Dataset Hugging Face revision
- Harness identifier and its commit / version
- Model identifier and snapshot date
- Full decoding parameters
- Prompt template actually sent to the model (one example per subtask)
- Raw outputs (kept for error analysis)
- Scores per subtask + overall
- Wall-clock time and total tokens

Results in the paper will link to an artifact containing all of the
above.

## 5. Known limitations

TBD — this section will track issues that affect evaluation validity
but are intentionally left unfixed. Expected categories:

- Ambiguous question wording (target: move to `DATA_ISSUES.md`).
- J-GAAP balance-sheet structure confusion (see error-analysis
  section of README).
- Temporal-reasoning format-compliance sensitivity.

## 6. Versioning

- Dataset revisions: tracked as Hugging Face commit hashes. Major
  dataset changes bump the `dataset_version` field in future rows.
- Task versions: the lm-eval mirror tracks upstream's `version` field
  (currently `0.3.0`).
- Package versions: standard semver on PyPI. Scoring behavior changes
  must bump the minor version and be noted in the CHANGELOG.

## 7. Related documents

- [`README.md`](../README.md) — user-facing overview, quick start,
  harness summary.
- [`lm_eval_tasks/README.md`](../lm_eval_tasks/README.md) — lm-eval
  mirror policy and sync workflow.
- `DATA_ISSUES.md` (**TBD**) — dataset quality log.
