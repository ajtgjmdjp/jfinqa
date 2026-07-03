#!/bin/bash
# Run baseline evaluation for all models on the full 1000-question dataset.
#
# Requires API keys: source ~/.tokens (OPENAI_API_KEY, GOOGLE_API_KEY).
# run_baseline.py resumes from existing __predictions.json files, so this
# script is safe to re-run after interruptions (no cleanup performed).

set -euo pipefail

cd "$(dirname "$0")/.."

DATA="scripts/data/final/jfinqa_v1.json"
OUT_DIR="scripts/data/baselines_full_1000"

echo "=========================================="
echo "jfinqa Full 1000 Baseline Evaluation"
echo "Data: ${DATA}"
echo "Output: ${OUT_DIR}"
echo "=========================================="

# model:regime pairs mirroring the published baseline set
# (gemini-2.5-pro is R1-only for cost reasons).
RUNS=(
    "gpt-5.4:R0" "gpt-5.4:R1"
    "gpt-5.4-mini:R0" "gpt-5.4-mini:R1"
    "gpt-5.4-nano:R0" "gpt-5.4-nano:R1"
    "gemini-2.5-flash:R0" "gemini-2.5-flash:R1"
    "gemini-2.5-flash-lite:R0" "gemini-2.5-flash-lite:R1"
    "gemini-2.5-pro:R1"
)

for run in "${RUNS[@]}"; do
    model="${run%%:*}"
    regime="${run##*:}"
    echo ""
    echo "===================="
    echo "Running: ${model} (${regime})"
    echo "===================="
    start_time=$(date +%s)

    uv run python -u scripts/run_baseline.py \
        --model "$model" \
        --regime "$regime" \
        --data "$DATA" \
        --out-dir "$OUT_DIR"

    end_time=$(date +%s)
    echo "Completed in $((end_time - start_time))s"
done

echo ""
echo "=========================================="
echo "All baseline evaluations completed!"
echo "=========================================="
echo ""
echo "Metrics:"
for run in "${RUNS[@]}"; do
    model="${run%%:*}"
    regime="${run##*:}"
    metrics="${OUT_DIR}/${model}__${regime}__metrics.json"
    if [ -f "$metrics" ]; then
        echo ""
        echo "--- ${model} (${regime}) ---"
        cat "$metrics"
    fi
done
