"""Build MBTI-style SFT dataset from anchor pairs with explicit combo balancing."""

from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from llm_client import TeacherConfig, chat_json, create_client
from mbti_profiles import INTENTS, MBTI_STYLES, SCENARIOS
from text_filters import sanitize_text, stable_hash


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


def make_input(context: str, mbti: str, scenario: str, intent: str) -> str:
    return (
        f"MBTI={mbti}\n"
        f"scenario={scenario}\n"
        f"intent={intent}\n"
        f"user_dialogue={context}"
    )


def synthesize_sample(
    client,
    cfg: TeacherConfig,
    *,
    anchor_context: str,
    anchor_reply: str,
    mbti: str,
    scenario: str,
    intent: str,
) -> Tuple[str, str]:
    style = MBTI_STYLES[mbti]
    prompt = f"""
请基于给定的“人类高质量锚点”，构造一条可训练样本（JSON）。

目标：
1) 生成一个符合目标场景的 user_context（1-3句）
2) 生成一个符合目标 intent 的高情商回复
3) 回复必须符合 MBTI={mbti} 的表达风格，不违背人格
4) 不说教、不过度模板化，语气自然
5) 回复长度 40-180 中文字

目标标签：
- scenario={scenario}
- intent={intent}
- mbti_style={style}

锚点参考（仅供语义参考，不要照抄）：
- anchor_context: {anchor_context}
- anchor_reply: {anchor_reply}

只输出 JSON：
{{
  "context": "...",
  "reply": "..."
}}
""".strip()

    data = chat_json(
        client=client,
        cfg=cfg,
        messages=[
            {"role": "system", "content": "你是高质量中文数据构造助手，只输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
        max_tokens=420,
    )
    context = sanitize_text(data.get("context", ""))
    reply = sanitize_text(data.get("reply", ""))
    return context, reply


def all_done(counts: Dict[Tuple[str, str, str], int], target: int, mbti_list: List[str]) -> bool:
    for mbti in mbti_list:
        for scenario in SCENARIOS:
            for intent in INTENTS:
                if counts[(mbti, scenario, intent)] < target:
                    return False
    return True


def lowest_combo(counts: Dict[Tuple[str, str, str], int], mbti_list: List[str]) -> Tuple[str, str, str]:
    candidates: List[Tuple[int, Tuple[str, str, str]]] = []
    for mbti in mbti_list:
        for scenario in SCENARIOS:
            for intent in INTENTS:
                key = (mbti, scenario, intent)
                candidates.append((counts[key], key))
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SFT dataset from anchors (balanced combos).")
    parser.add_argument("--anchors-jsonl", type=str, default="training/data/raw/anchors.jsonl")
    parser.add_argument("--output-jsonl", type=str, default="training/data/processed/sft_candidates.jsonl")
    parser.add_argument("--target-per-combo", type=int, default=40)
    parser.add_argument("--max-total", type=int, default=3600)
    parser.add_argument("--min-len", type=int, default=40)
    parser.add_argument("--max-len", type=int, default=180)
    parser.add_argument("--mbti-list", type=str, default="INTJ,ENFP,ISTJ,ESFP")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    anchors = [x for x in read_jsonl(Path(args.anchors_jsonl)) if x.get("context") and x.get("anchor_reply")]
    if not anchors:
        raise ValueError("No anchors found.")

    mbti_list = [x.strip().upper() for x in args.mbti_list.split(",") if x.strip()]
    for m in mbti_list:
        if m not in MBTI_STYLES:
            raise ValueError(f"Unsupported MBTI in this phase: {m}")

    if args.dry_run:
        client = None
        cfg = None
    else:
        cfg = TeacherConfig.from_env()
        client = create_client(cfg)

    counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
    rows: List[Dict] = []
    seen_ids = set()
    attempts = 0
    max_attempts = args.max_total * 10

    while (
        not all_done(counts, args.target_per_combo, mbti_list)
        and len(rows) < args.max_total
        and attempts < max_attempts
    ):
        mbti, scenario, intent = lowest_combo(counts, mbti_list)
        if counts[(mbti, scenario, intent)] >= args.target_per_combo:
            # If all combos reached target but all_done not triggered due some issue.
            if all_done(counts, args.target_per_combo, mbti_list):
                break
            attempts += 1
            continue

        anchor = random.choice(anchors)
        anchor_context = sanitize_text(anchor.get("context", ""))
        anchor_reply = sanitize_text(anchor.get("anchor_reply", ""))
        if not anchor_context or not anchor_reply:
            attempts += 1
            continue

        attempts += 1
        try:
            if args.dry_run:
                context = sanitize_text(
                    f"在{scenario}场景中，对方提出了让我不舒服的请求，我希望以{intent}为目标进行回应。"
                )
                output = sanitize_text(
                    f"（{mbti}）我理解你的诉求，也希望沟通保持高效。我们先把边界和可执行安排说清楚，这样双方都更容易接受。"
                )
            else:
                context, output = synthesize_sample(
                    client=client,
                    cfg=cfg,
                    anchor_context=anchor_context,
                    anchor_reply=anchor_reply,
                    mbti=mbti,
                    scenario=scenario,
                    intent=intent,
                )

            if not context or not output:
                continue
            if len(output) < args.min_len or len(output) > args.max_len:
                continue

            input_text = make_input(context=context, mbti=mbti, scenario=scenario, intent=intent)
            row_id = stable_hash(input_text + output)
            if row_id in seen_ids:
                continue

            row = {
                "id": row_id,
                "instruction": "你是MBTI风格化社交助手。请生成高情商、边界清晰、自然可接受的回复。",
                "input": input_text,
                "output": output,
                "meta": {
                    "mbti": mbti,
                    "scenario": scenario,
                    "intent": intent,
                    "anchor_id": anchor.get("id", ""),
                    "source": anchor.get("source_platform", "unknown"),
                },
            }
            rows.append(row)
            seen_ids.add(row_id)
            counts[(mbti, scenario, intent)] += 1

            if len(rows) % 50 == 0:
                print(f"progress: rows={len(rows)}, attempts={attempts}")
        except Exception as exc:  # noqa: BLE001
            print(f"[synthesize failed] ({mbti},{scenario},{intent}) err={exc}")

    write_jsonl(Path(args.output_jsonl), rows)
    print(f"done. output={args.output_jsonl} rows={len(rows)} attempts={attempts}")
    for mbti in mbti_list:
        for scenario in SCENARIOS:
            for intent in INTENTS:
                key = (mbti, scenario, intent)
                print(f"{mbti}/{scenario}/{intent}: {counts[key]}")


if __name__ == "__main__":
    main()

