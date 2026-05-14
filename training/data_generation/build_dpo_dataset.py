"""Construct DPO preference pairs from SFT prompts."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from llm_client import TeacherConfig, chat_json, chat_text, create_client
from text_filters import sanitize_text


TEMPERATURES = [0.2, 0.7, 1.0]


def read_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def generate_candidate(client, cfg: TeacherConfig, instruction: str, input_text: str, temperature: float) -> str:
    prompt = f"{instruction}\n\n{input_text}\n\n请只输出一条回复正文。"
    text = chat_text(
        client=client,
        cfg=cfg,
        messages=[
            {"role": "system", "content": "你是高质量中文对话助手。"},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=300,
    )
    return sanitize_text(text)


def judge_candidates(client, cfg: TeacherConfig, instruction: str, input_text: str, candidates: List[str]) -> List[Tuple[float, str]]:
    joined = "\n".join([f"[候选{i+1}] {c}" for i, c in enumerate(candidates)])
    prompt = f"""
请对以下候选回复做评分（1-5），评分维度：风格一致性、意图达成、边界感、自然度、安全性。
输出 JSON:
{{
  "scores": [
    {{"idx": 1, "total": 4.7}},
    {{"idx": 2, "total": 3.8}}
  ]
}}

instruction: {instruction}
input: {input_text}

候选：
{joined}
""".strip()

    data = chat_json(
        client=client,
        cfg=cfg,
        messages=[
            {"role": "system", "content": "你是严格评测员，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=400,
    )

    scores = []
    for item in data.get("scores", []):
        try:
            idx = int(item["idx"]) - 1
            total = float(item["total"])
            if 0 <= idx < len(candidates):
                scores.append((total, candidates[idx]))
        except Exception:
            continue
    return sorted(scores, key=lambda x: x[0], reverse=True)


def split_train_val(rows: List[Dict], val_ratio: float = 0.1) -> Tuple[List[Dict], List[Dict]]:
    random.shuffle(rows)
    n_val = int(len(rows) * val_ratio)
    return rows[n_val:], rows[:n_val]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build DPO pairs from SFT prompts.")
    parser.add_argument("--sft-train-jsonl", type=str, default="training/data/processed/sft_train.jsonl")
    parser.add_argument("--train-out", type=str, default="training/data/processed/dpo_train.jsonl")
    parser.add_argument("--val-out", type=str, default="training/data/processed/dpo_val.jsonl")
    parser.add_argument("--max-prompts", type=int, default=1000)
    parser.add_argument("--max-pairs", type=int, default=1000)
    parser.add_argument("--min-gap", type=float, default=1.5)
    parser.add_argument("--max-len-ratio", type=float, default=2.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    samples = list(read_jsonl(Path(args.sft_train_jsonl)))
    if not samples:
        raise ValueError("No SFT train samples found.")

    selected = samples[: args.max_prompts]
    pairs: List[Dict] = []

    if args.dry_run:
        client = None
        cfg = None
    else:
        cfg = TeacherConfig.from_env()
        client = create_client(cfg)

    for idx, s in enumerate(selected, start=1):
        instruction = s.get("instruction", "")
        input_text = s.get("input", "")
        if not instruction or not input_text:
            continue

        try:
            if args.dry_run:
                candidates = [
                    "我理解你的意思。我们先把事实对齐，再确定边界和后续安排。",
                    "你说得不对，我不接受你的说法。",
                    "先冷静，我们按事实和目标来沟通，这样更容易达成一致。",
                ]
                ranked = [(4.6, candidates[0]), (3.9, candidates[2]), (2.8, candidates[1])]
            else:
                candidates = [
                    generate_candidate(client, cfg, instruction, input_text, t)
                    for t in TEMPERATURES
                ]
                candidates = [c for c in candidates if c]
                if len(candidates) < 2:
                    continue
                ranked = judge_candidates(client, cfg, instruction, input_text, candidates)
                if len(ranked) < 2:
                    continue

            best_score, chosen = ranked[0]
            worst_score, rejected = ranked[-1]
            score_gap = best_score - worst_score
            if score_gap < args.min_gap:
                continue

            c_len = max(1, len(chosen))
            r_len = max(1, len(rejected))
            ratio = max(c_len, r_len) / min(c_len, r_len)
            if ratio > args.max_len_ratio:
                continue

            pair = {
                "instruction": instruction,
                "input": input_text,
                "chosen": sanitize_text(chosen),
                "rejected": sanitize_text(rejected),
                "meta": {
                    "score_gap": round(score_gap, 4),
                    "from_sft_id": s.get("id", ""),
                },
            }
            pairs.append(pair)
            if len(pairs) >= args.max_pairs:
                break
        except Exception as exc:  # noqa: BLE001
            print(f"[dpo pair failed] idx={idx} err={exc}")

        if idx % 50 == 0:
            print(f"progress: prompts={idx}/{len(selected)}, pairs={len(pairs)}")

    train_rows, val_rows = split_train_val(pairs, val_ratio=0.1)
    write_jsonl(Path(args.train_out), train_rows)
    write_jsonl(Path(args.val_out), val_rows)
    print(f"done. dpo_train={len(train_rows)} dpo_val={len(val_rows)}")


if __name__ == "__main__":
    main()

