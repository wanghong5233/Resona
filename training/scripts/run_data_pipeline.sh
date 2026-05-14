#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${ROOT_DIR}"

echo "[1/4] Extract anchors..."
python training/data_generation/extract_anchor_pairs.py \
  --input-jsonl training/data/raw/xhs_candidates.jsonl \
  --output-jsonl training/data/raw/anchors.jsonl \
  --max-records 1200

echo "[2/4] Build SFT candidates..."
python training/data_generation/build_sft_dataset.py \
  --anchors-jsonl training/data/raw/anchors.jsonl \
  --output-jsonl training/data/processed/sft_candidates.jsonl \
  --target-per-combo 40 \
  --max-total 3600

echo "[3/4] Filter SFT and split..."
python training/data_generation/filter_sft_dataset.py \
  --input-jsonl training/data/processed/sft_candidates.jsonl \
  --train-out training/data/processed/sft_train.jsonl \
  --val-out training/data/processed/sft_val.jsonl \
  --report-out training/reports/data_qc_report.md \
  --enable-judge

echo "[4/4] Build DPO pairs..."
python training/data_generation/build_dpo_dataset.py \
  --sft-train-jsonl training/data/processed/sft_train.jsonl \
  --train-out training/data/processed/dpo_train.jsonl \
  --val-out training/data/processed/dpo_val.jsonl \
  --max-prompts 1000 \
  --max-pairs 1000 \
  --min-gap 1.5

echo "Data pipeline done."

