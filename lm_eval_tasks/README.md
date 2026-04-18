# jfinqa — lm-evaluation-harness task mirror

This directory is a canonical mirror of the jfinqa task as merged into
[EleutherAI/lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)
via [PR #3570](https://github.com/EleutherAI/lm-evaluation-harness/pull/3570)
(merged 2026-03-18, commit `eb9253ae7ce21ef2027b94cf5c93c9b44e8aec32`).

## Why this mirror exists

Most users should rely on the upstream copy bundled with lm-eval. This
mirror is kept in the jfinqa repository for three reasons:

1. **Self-contained evaluation.** Users who clone this repo can run the
   task without also cloning lm-eval.
2. **Reproducibility.** The commit-pinned mirror lets papers and
   benchmarks cite an exact task definition that cannot silently change.
3. **Drift detection.** `scripts/sync_lm_eval.py` compares these files
   against upstream and reports any divergence.

## Files

| File                         | Purpose                                         |
|------------------------------|-------------------------------------------------|
| `_jfinqa.yaml`               | group definition aggregating the three subtasks |
| `jfinqa_numerical.yaml`      | numerical reasoning subtask (550 questions)     |
| `jfinqa_consistency.yaml`    | consistency checking subtask (200 questions)    |
| `jfinqa_temporal.yaml`       | temporal reasoning subtask (250 questions)      |
| `utils.py`                   | prompt formatting and scoring helpers           |

The scoring logic in `utils.py` intentionally mirrors
[`src/jfinqa/_metrics.py`](../src/jfinqa/_metrics.py). When either side
changes, both must be updated. The integration tests in
[`tests/test_lm_eval_integration.py`](../tests/test_lm_eval_integration.py)
pin a shared set of golden cases and fail if the two implementations
diverge.

## Updating this mirror

To check for upstream drift:

```bash
uv run python scripts/sync_lm_eval.py
```

To overwrite the local mirror with the current upstream:

```bash
uv run python scripts/sync_lm_eval.py --apply
```

After applying, run the integration tests to confirm the jfinqa package
and the mirror still agree:

```bash
uv run pytest tests/test_lm_eval_integration.py -q
```

## Running the task

Assuming lm-evaluation-harness is installed, point it at this directory:

```bash
lm_eval \
  --model hf \
  --model_args pretrained=meta-llama/Llama-3.2-3B-Instruct \
  --tasks jfinqa \
  --include_path lm_eval_tasks \
  --batch_size auto
```
