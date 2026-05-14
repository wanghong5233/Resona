"""Hard/soft filtering for SFT candidates and stratified train/val split."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from llm_client import TeacherConfig, chat_json, create_client
from text_filters import jaccard_similarity, normalize_text, sanitize_text


RISK_WORDS = ["去死", "废物", "垃圾", "你不配", "滚", "威胁", "诈骗", "裸照", "曝光你"]
TEMPLATE_PHRASES = ["我完全理解你的感受", "作为一个", "基于以上三点", "综上所述"]


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


def trigrams(s: str) -> set:
    t = normalize_text(s)
    if len(t) < 3:
        return {t} if t else set()
    return {t[i : i + 3] for i in range(len(t) - 2)}


def near_dup(a: str, b: str, threshold: float = 0.9) -> bool:
    return jaccard_similarity(trigrams(a), trigrams(b)) >= threshold


def judge_sample(client, cfg: TeacherConfig, sample: Dict) -> Dict:
    prompt = f"""
请给以下样本打分（1-5 分），并输出 JSON：
- style_consistency
- intent_fulfillment
- boundary_clarity
- naturalness
- safety
- avg
- verdict（pass/reject）
- reason（简短）

样本：
instruction: {sample.get("instruction", "")}
input: {sample.get("input", "")}
output: {sample.get("output", "")}
""".strip()

    data = chat_json(
        client=client,
        cfg=cfg,
        messages=[
            {"role": "system", "content": "你是严格的数据质检员，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=300,
    )
    return data


def split_stratified(rows: List[Dict], val_ratio: float = 0.1) -> Tuple[List[Dict], List[Dict]]:
    buckets: Dict[Tuple[str, str, str], List[Dict]] = defaultdict(list)
    for r in rows:
        m = r.get("meta", {})
        key = (m.get("mbti", "UNK"), m.get("scenario", "UNK"), m.get("intent", "UNK"))
        buckets[key].append(r)

    train, val = [], []
    for _, items in buckets.items():
        random.shuffle(items)
        n_val = max(1, int(len(items) * val_ratio)) if len(items) >= 10 else 0
        val.extend(items[:n_val])
        train.extend(items[n_val:])
    return train, val


def main() -> None:
    parser = argparse.ArgumentParser(description="Filter SFT candidates and split train/val.")
    parser.add_argument("--input-jsonl", type=str, default="training/data/processed/sft_candidates.jsonl")
    parser.add_argument("--train-out", type=str, default="training/data/processed/sft_train.jsonl")
    parser.add_argument("--val-out", type=str, default="training/data/processed/sft_val.jsonl")
    parser.add_argument("--report-out", type=str, default="training/reports/data_qc_report.md")
    parser.add_argument("--min-len", type=int, default=40)
    parser.add_argument("--max-len", type=int, default=180)
    parser.add_argument("--near-dup-threshold", type=float, default=0.9)
    parser.add_argument("--enable-judge", action="store_true")
    parser.add_argument("--judge-limit", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    rows = list(read_jsonl(Path(args.input_jsonl)))
    total = len(rows)

    filtered: List[Dict] = []
    dedup_cache: List[str] = []
    stats = defaultdict(int)

    cfg = None
    client = None
    if args.enable_judge:
        cfg = TeacherConfig.from_env()
        client = create_client(cfg)

    for row in rows:
        output = sanitize_text(row.get("output", ""))
        if not row.get("instruction") or not row.get("input") or not output:
            stats["drop_missing_fields"] += 1
            continue
        if len(output) < args.min_len or len(output) > args.max_len:
            stats["drop_len"] += 1
            continue
        if any(w in output for w in RISK_WORDS):
            stats["drop_risk_words"] += 1
            continue
        if sum(1 for p in TEMPLATE_PHRASES if p in output) >= 2:
            stats["drop_template"] += 1
            continue

        # Near duplicate check (against already kept outputs only).
        duplicated = False
        for prev in dedup_cache[-500:]:
            if near_dup(prev, output, threshold=args.near_dup_threshold):
                duplicated = True
                break
        if duplicated:
            stats["drop_near_dup"] += 1
            continue

        row["output"] = output
        stats["pass_hard_rules"] += 1

        if args.enable_judge and len(filtered) < args.judge_limit:
            try:
                j = judge_sample(client, cfg, row)
                avg = float(j.get("avg", 0.0) or 0.0)
                safety = float(j.get("safety", 0.0) or 0.0)
                verdict = str(j.get("verdict", "")).lower()
                if avg < 4.2 or safety < 4.5 or verdict == "reject":
                    stats["drop_judge"] += 1
                    continue
                row.setdefault("meta", {})["judge"] = j
            except Exception as exc:  # noqa: BLE001
                stats["judge_error_keep"] += 1
                row.setdefault("meta", {})["judge_error"] = str(exc)[:200]

        filtered.append(row)
        dedup_cache.append(output)

    train_rows, val_rows = split_stratified(filtered, val_ratio=0.1)
    write_jsonl(Path(args.train_out), train_rows)
    write_jsonl(Path(args.val_out), val_rows)

    report = Path(args.report_out)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        (
            "# Data QC Report\n\n"
            f"- Input candidates: {total}\n"
            f"- Hard-rule passed: {stats['pass_hard_rules']}\n"
            f"- Final kept: {len(filtered)}\n"
            f"- Train: {len(train_rows)}\n"
            f"- Val: {len(val_rows)}\n\n"
            "## Drop Stats\n"
            + "\n".join(f"- {k}: {v}" for k, v in sorted(stats.items()) if k.startswith("drop_"))
            + "\n"
        ),
        encoding="utf-8",
    )

    print(f"done. kept={len(filtered)} train={len(train_rows)} val={len(val_rows)}")


if __name__ == "__main__":
    main()

