#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

cp "training/configs/dataset_info.json" "training/data/processed/dataset_info.json"
LFACTORY_CMD="${LFACTORY_CMD:-llamafactory-cli}"

echo "[SFT-SMOKE] Running quick smoke test..."
${LFACTORY_CMD} train \
  "training/configs/sft_qwen7b_lora.yaml" \
  --max_samples 200 \
  --num_train_epochs 0.2 \
  --save_steps 50 \
  --eval_steps 50 \
  --output_dir "training/outputs/checkpoints/sft_lora_smoke"

echo "[SFT-SMOKE] Done."
