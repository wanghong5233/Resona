"""Lightweight OpenAI-compatible client for data generation scripts."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI


def _load_env_file(path: str) -> None:
    """Very small .env loader (does not override existing env vars)."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except FileNotFoundError:
        return


def load_default_env() -> None:
    """Load repo's env files if present (best-effort)."""
    # repo_root/training/data_generation/llm_client.py -> repo_root is parents[2]
    here = os.path.abspath(__file__)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(here), "..", ".."))
    _load_env_file(os.path.join(repo_root, ".env"))
    _load_env_file(os.path.join(repo_root, "backend", ".env"))
    _load_env_file(os.path.join(repo_root, "training", ".env"))


@dataclass
class TeacherConfig:
    api_key: str
    base_url: str
    model: str
    timeout: int = 60
    max_retries: int = 3
    retry_backoff_sec: float = 1.5

    @classmethod
    def from_env(cls) -> "TeacherConfig":
        load_default_env()

        api_key = os.getenv("TEACHER_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise ValueError("Missing TEACHER_API_KEY (or OPENAI_API_KEY)")

        return cls(
            api_key=api_key,
            base_url=(
                os.getenv("TEACHER_BASE_URL", "").strip()
                or os.getenv("OPENAI_BASE_URL", "").strip()
                or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            ),
            model=(os.getenv("TEACHER_MODEL", "").strip() or os.getenv("OPENAI_MODEL_NAME", "").strip() or "qwen-plus"),
            timeout=int(os.getenv("TEACHER_TIMEOUT", "60")),
            max_retries=int(os.getenv("TEACHER_MAX_RETRIES", "3")),
            retry_backoff_sec=float(os.getenv("TEACHER_RETRY_BACKOFF_SEC", "1.5")),
        )


def create_client(cfg: TeacherConfig) -> OpenAI:
    return OpenAI(api_key=cfg.api_key, base_url=cfg.base_url, timeout=cfg.timeout)


def _strip_code_fence(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        lines = raw.splitlines()
        # Remove the first and last fences if present.
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return raw


def chat_text(
    client: OpenAI,
    cfg: TeacherConfig,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 600,
) -> str:
    last_err: Optional[Exception] = None
    for i in range(cfg.max_retries):
        try:
            resp = client.chat.completions.create(
                model=cfg.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = resp.choices[0].message.content or ""
            return _strip_code_fence(content)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            if i < cfg.max_retries - 1:
                time.sleep(cfg.retry_backoff_sec * (2**i))
    raise RuntimeError(f"chat_text failed after retries: {last_err}") from last_err


def chat_json(
    client: OpenAI,
    cfg: TeacherConfig,
    messages: List[Dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 600,
) -> Dict[str, Any]:
    text = chat_text(
        client=client,
        cfg=cfg,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Best effort: extract the first JSON object block.
        l = text.find("{")
        r = text.rfind("}")
        if l >= 0 and r > l:
            return json.loads(text[l : r + 1])
        raise

