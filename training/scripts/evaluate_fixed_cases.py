"""Compare Base vs SFT vs DPO on fixed eval cases via OpenAI-compatible endpoint."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

from openai import OpenAI


def read_jsonl(path: Path) -> List[Dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def ask(client: OpenAI, model: str, case: Dict) -> str:
    user_prompt = (
        "请生成一条高情商回复。\n"
        f"MBTI={case['mbti']}\n"
        f"scenario={case['scenario']}\n"
        f"intent={case['intent']}\n"
        f"dialogue={case['dialogue']}\n"
        "只输出回复正文。"
    )
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是MBTI风格化社交助手。"},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.6,
        max_tokens=260,
    )
    return (resp.choices[0].message.content or "").strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare outputs of multiple models on fixed cases.")
    parser.add_argument("--cases-jsonl", type=str, default="training/data/raw/eval_cases.jsonl")
    parser.add_argument("--report-md", type=str, default="training/reports/model_eval_report.md")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8001/v1")
    parser.add_argument("--api-key", type=str, default="EMPTY")
    parser.add_argument("--model-base", type=str, default="")
    parser.add_argument("--model-sft", type=str, default="")
    parser.add_argument("--model-dpo", type=str, default="")
    args = parser.parse_args()

    rows = read_jsonl(Path(args.cases_jsonl))
    if not rows:
        raise ValueError("No eval cases found.")

    client = OpenAI(api_key=args.api_key, base_url=args.base_url)
    model_map = {
        "Base": args.model_base.strip(),
        "SFT": args.model_sft.strip(),
        "DPO": args.model_dpo.strip(),
    }
    enabled = {k: v for k, v in model_map.items() if v}
    if not enabled:
        raise ValueError("Provide at least one model id via --model-base/--model-sft/--model-dpo")

    lines = ["# Model Eval Report", ""]
    for i, case in enumerate(rows, start=1):
        lines.append(f"## Case {i}")
        lines.append(f"- MBTI: `{case['mbti']}`")
        lines.append(f"- Scenario: `{case['scenario']}`")
        lines.append(f"- Intent: `{case['intent']}`")
        lines.append(f"- Dialogue: {case['dialogue']}")
        lines.append("")
        for name, model in enabled.items():
            try:
                reply = ask(client, model, case)
            except Exception as exc:  # noqa: BLE001
                reply = f"[ERROR] {exc}"
            lines.append(f"### {name}")
            lines.append(reply)
            lines.append("")

    report = Path(args.report_md)
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines), encoding="utf-8")
    print(f"done. report={report}")


if __name__ == "__main__":
    main()

