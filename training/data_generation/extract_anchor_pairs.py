"""Extract (context, anchor_reply) pairs from raw collected text with desensitization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Iterable, List

from llm_client import TeacherConfig, chat_json, create_client
from mbti_profiles import normalize_intent, normalize_scenario
from text_filters import sanitize_text, stable_hash


SYSTEM_PROMPT = (
    "你是数据清洗助手。任务：从原始社交文本中抽取可用于训练的数据锚点。"
    "请严格输出 JSON，不要额外解释。"
)


def read_jsonl(path: Path) -> Iterable[Dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def write_jsonl(path: Path, rows: List[Dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_source_text_from_pair(pair: Dict) -> str:
    """从 dialogue_pairs 中的单条对话对构建待抽取文本。不包含正文。"""
    inp = sanitize_text(pair.get("input", "") or "")
    out = sanitize_text(pair.get("output", "") or "")
    likes = pair.get("output_likes") or pair.get("output_likes_raw") or ""
    if likes:
        return f"父评论（用户发言）: {inp}\n高赞回复（点赞={likes}）: {out}".strip()
    return f"父评论（用户发言）: {inp}\n高赞回复: {out}".strip()


def extract_one(client, cfg: TeacherConfig, source_text: str) -> Dict:
    user_prompt = f"""
请从下面「评论区对话对」抽取训练锚点，输出 JSON。注意：这是评论区数据，没有正文。
- context: 1-3 句，根据父评论归纳场景和沟通目标（不保留隐私信息）
- anchor_reply: 直接参考高赞回复，保持其高情商表达，人类可接受、边界清晰、自然不说教
- scenario: 仅可取 workplace/intimate/family/social
- intent: 仅可取 refuse/boundary/request/clarify/comfort
- confidence: 0-1 的置信度

评论区对话对：
{source_text}

仅输出 JSON，示例：
{{
  "context": "...",
  "anchor_reply": "...",
  "scenario": "workplace",
  "intent": "boundary",
  "confidence": 0.84
}}
""".strip()

    data = chat_json(
        client=client,
        cfg=cfg,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=500,
    )
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract desensitized anchor pairs from raw JSONL.")
    parser.add_argument("--input-jsonl", type=str, required=True)
    parser.add_argument("--output-jsonl", type=str, default="training/data/raw/anchors.jsonl")
    parser.add_argument("--max-records", type=int, default=1200)
    parser.add_argument("--min-content-len", type=int, default=40)
    parser.add_argument("--min-confidence", type=float, default=0.55)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    src = Path(args.input_jsonl)
    if not src.exists():
        raise FileNotFoundError(src)

    rows: List[Dict] = []
    seen_ids = set()
    if args.dry_run:
        client = None
        cfg = None
    else:
        cfg = TeacherConfig.from_env()
        client = create_client(cfg)

    for idx, item in enumerate(read_jsonl(src), start=1):
        if len(rows) >= args.max_records:
            break

        pairs = item.get("dialogue_pairs") or []
        if not pairs:
            continue

        for pair_idx, pair in enumerate(pairs):
            if len(rows) >= args.max_records:
                break

            source_text = build_source_text_from_pair(pair)
            if len(source_text) < args.min_content_len:
                continue

            try:
                if args.dry_run:
                    parsed = {
                        "context": source_text[:160],
                        "anchor_reply": "我理解你的诉求。我们先把事实和边界对齐，再给出一个双方都能执行的方案。",
                        "scenario": "social",
                        "intent": "clarify",
                        "confidence": 0.5,
                    }
                else:
                    parsed = extract_one(client, cfg, source_text)

                context = sanitize_text(parsed.get("context", ""))
                anchor_reply = sanitize_text(parsed.get("anchor_reply", ""))
                if not context or not anchor_reply:
                    continue

                scenario = normalize_scenario(parsed.get("scenario", ""))
                intent = normalize_intent(parsed.get("intent", ""))
                confidence = float(parsed.get("confidence", 0.0) or 0.0)
                if not args.dry_run and confidence < args.min_confidence:
                    continue

                record = {
                    "id": stable_hash((item.get("url", "") or "") + str(pair_idx) + context + anchor_reply),
                    "source_platform": item.get("platform", "unknown"),
                    "source_url": "",
                    "context": context,
                    "anchor_reply": anchor_reply,
                    "scenario": scenario,
                    "intent": intent,
                    "confidence": max(0.0, min(1.0, confidence)),
                    "meta": {
                        "output_likes": pair.get("output_likes") or pair.get("output_likes_raw"),
                        "raw_len": len(source_text),
                    },
                }
                if record["id"] in seen_ids:
                    continue
                seen_ids.add(record["id"])
                rows.append(record)
            except Exception as exc:  # noqa: BLE001
                print(f"[extract failed] item={idx} pair={pair_idx} err={exc}")

        if idx % 50 == 0:
            print(f"progress: items={idx}, extracted={len(rows)}")

    write_jsonl(Path(args.output_jsonl), rows)
    print(f"done. output={args.output_jsonl}, total={len(rows)}")


if __name__ == "__main__":
    main()

