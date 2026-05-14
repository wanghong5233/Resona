from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import median
from typing import Dict, Iterable, List


def read_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def pct(part: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return 100.0 * part / total


def p90(nums: List[int]) -> int:
    if not nums:
        return 0
    s = sorted(nums)
    idx = int(0.9 * (len(s) - 1))
    return s[idx]


def main() -> None:
    parser = argparse.ArgumentParser(description="Report high-like coverage for xhs_candidates.jsonl")
    parser.add_argument("--input-jsonl", type=str, default="training/data/raw/xhs_candidates.jsonl")
    parser.add_argument("--like-threshold", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    src = Path(args.input_jsonl)
    if not src.exists():
        raise FileNotFoundError(src)

    total_notes = 0
    notes_with_pairs = 0
    notes_with_high_like = 0
    total_pairs = 0
    high_like_pairs_count = 0
    all_positive_likes: List[int] = []
    top_examples: List[Dict] = []

    for item in read_jsonl(src):
        total_notes += 1
        pairs = item.get("dialogue_pairs") or []
        ps = item.get("pair_stats") or item.get("comment_stats") or {}

        if pairs:
            notes_with_pairs += 1

        note_has_high_like = False
        for p in pairs:
            if not isinstance(p, dict):
                continue
            raw = p.get("output_likes") or p.get("output_likes_raw") or 0
            try:
                likes = int(raw) if raw else 0
            except (ValueError, TypeError):
                likes = 0
            txt = (p.get("output", "") or "").strip()
            total_pairs += 1
            if likes > 0:
                all_positive_likes.append(likes)
            if likes >= args.like_threshold:
                high_like_pairs_count += 1
                note_has_high_like = True
                top_examples.append(
                    {
                        "url": item.get("url", ""),
                        "likes": likes,
                        "text": txt[:120],
                    }
                )

        if note_has_high_like:
            notes_with_high_like += 1

    top_examples.sort(key=lambda x: x["likes"], reverse=True)
    top_examples = top_examples[: max(0, args.top_k)]

    print("=== High-Like Coverage Report (dialogue_pairs) ===")
    print(f"input_jsonl: {src}")
    print(f"like_threshold: {args.like_threshold}")
    print("")
    print(f"total_notes: {total_notes}")
    print(
        f"notes_with_dialogue_pairs: {notes_with_pairs} "
        f"({pct(notes_with_pairs, total_notes):.1f}%)"
    )
    print(
        f"notes_with_high_like_pairs: {notes_with_high_like} "
        f"({pct(notes_with_high_like, total_notes):.1f}%)"
    )
    print(f"total_dialogue_pairs: {total_pairs}")
    print(
        f"high_like_pairs (output_likes>={args.like_threshold}): {high_like_pairs_count} "
        f"({pct(high_like_pairs_count, total_pairs):.1f}%)"
    )

    if all_positive_likes:
        print(f"likes_p50: {int(median(all_positive_likes))}")
        print(f"likes_p90: {p90(all_positive_likes)}")
        print(f"likes_max: {max(all_positive_likes)}")
    else:
        print("likes_p50: 0")
        print("likes_p90: 0")
        print("likes_max: 0")

    if top_examples:
        print("")
        print("top_examples:")
        for i, ex in enumerate(top_examples, start=1):
            print(f"{i}. likes={ex['likes']} url={ex['url']}")
            print(f"   text={ex['text']}")


if __name__ == "__main__":
    main()
