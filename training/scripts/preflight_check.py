"""Preflight checks before expensive SFT/DPO training."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def read_jsonl(path: Path) -> List[Dict]:
    rows: List[Dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sft_combo_key(row: Dict) -> Tuple[str, str, str]:
    meta = row.get("meta", {})
    return (
        str(meta.get("mbti", "UNK")),
        str(meta.get("scenario", "UNK")),
        str(meta.get("intent", "UNK")),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Check dataset sanity before training.")
    parser.add_argument("--sft-train", type=str, default="training/data/processed/sft_train.jsonl")
    parser.add_argument("--sft-val", type=str, default="training/data/processed/sft_val.jsonl")
    parser.add_argument("--dpo-train", type=str, default="training/data/processed/dpo_train.jsonl")
    parser.add_argument("--dpo-val", type=str, default="training/data/processed/dpo_val.jsonl")
    parser.add_argument("--min-sft-train", type=int, default=2500)
    parser.add_argument("--min-dpo-train", type=int, default=700)
    parser.add_argument("--min-combo-count", type=int, default=20)
    args = parser.parse_args()

    critical_errors = []
    warnings = []

    paths = [Path(args.sft_train), Path(args.sft_val), Path(args.dpo_train), Path(args.dpo_val)]
    for p in paths:
        if not p.exists():
            critical_errors.append(f"missing file: {p}")

    if critical_errors:
        print("❌ Preflight failed:")
        for e in critical_errors:
            print(f"- {e}")
        raise SystemExit(1)

    sft_train = read_jsonl(Path(args.sft_train))
    sft_val = read_jsonl(Path(args.sft_val))
    dpo_train = read_jsonl(Path(args.dpo_train))
    dpo_val = read_jsonl(Path(args.dpo_val))

    if len(sft_train) < args.min_sft_train:
        warnings.append(f"sft_train too small: {len(sft_train)} < {args.min_sft_train}")
    if len(dpo_train) < args.min_dpo_train:
        warnings.append(f"dpo_train too small: {len(dpo_train)} < {args.min_dpo_train}")

    # SFT field checks
    for i, r in enumerate(sft_train[:200], start=1):
        if not r.get("instruction") or not r.get("input") or not r.get("output"):
            critical_errors.append(f"sft_train row {i} missing instruction/input/output")
            break
        out_len = len(str(r.get("output", "")))
        if out_len < 30 or out_len > 260:
            warnings.append(f"sft_train row {i} output length unusual: {out_len}")
            break

    # Combo distribution checks.
    combo_counts = Counter(sft_combo_key(r) for r in sft_train)
    if len(combo_counts) < 60:  # expect close to 80 for 4x4x5
        warnings.append(f"combo coverage low: {len(combo_counts)} unique combos")
    low_combo = [k for k, v in combo_counts.items() if v < args.min_combo_count]
    if low_combo:
        warnings.append(f"{len(low_combo)} combos have count < {args.min_combo_count}")

    # DPO checks
    for i, r in enumerate(dpo_train[:200], start=1):
        if not r.get("instruction") or not r.get("input") or not r.get("chosen") or not r.get("rejected"):
            critical_errors.append(f"dpo_train row {i} missing required fields")
            break
        if str(r.get("chosen")).strip() == str(r.get("rejected")).strip():
            warnings.append(f"dpo_train row {i} chosen equals rejected")
            break

    print("=== Preflight Summary ===")
    print(f"SFT train: {len(sft_train)} | SFT val: {len(sft_val)}")
    print(f"DPO train: {len(dpo_train)} | DPO val: {len(dpo_val)}")
    print(f"SFT combos: {len(combo_counts)}")

    if warnings:
        print("\n⚠️ Warnings:")
        for w in warnings:
            print(f"- {w}")

    if critical_errors:
        print("\n❌ Critical errors:")
        for e in critical_errors:
            print(f"- {e}")
        raise SystemExit(1)

    print("\n✅ Preflight passed (no critical error).")


if __name__ == "__main__":
    main()

