#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

echo "[SFT] Preparing dataset info..."
cp "training/configs/dataset_info.json" "training/data/processed/dataset_info.json"

LFACTORY_CMD="${LFACTORY_CMD:-llamafactory-cli}"

echo "[SFT] Start training with config: training/configs/sft_qwen7b_lora.yaml"
${LFACTORY_CMD} train "training/configs/sft_qwen7b_lora.yaml"

echo "[SFT] Done."
