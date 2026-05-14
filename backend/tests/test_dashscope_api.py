#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 DashScope API Key 是否有效。

安全约束：
- 严禁把真实 API Key 硬编码在源码里。
- 真实 Key 只允许通过环境变量 DASHSCOPE_API_KEY 传入。
- .env 文件已在 .gitignore 中，请把真实 Key 写到本地 .env 或在终端 export。
"""

import io
import json
import os
import sys

import httpx


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


API_KEY = os.environ.get("DASHSCOPE_API_KEY", "").strip()
BASE_URL = os.environ.get(
    "DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
MODEL_NAME = os.environ.get("DASHSCOPE_MODEL_NAME", "qwen-plus")


def _redact(key: str) -> str:
    if not key:
        return "(empty)"
    if len(key) <= 12:
        return "***"
    return f"{key[:4]}...{key[-4:]}"


def test_dashscope_api() -> None:
    print("=" * 60)
    print("DashScope API Key 测试")
    print("=" * 60)

    if not API_KEY:
        print(
            "[FATAL] 未检测到环境变量 DASHSCOPE_API_KEY。\n"
            "请先在本地 .env 文件设置（已在 .gitignore 中），或在终端临时 export 后再运行：\n"
            "  PowerShell:  $env:DASHSCOPE_API_KEY = 'sk-xxxxxxxx'\n"
            "  bash:        export DASHSCOPE_API_KEY=sk-xxxxxxxx"
        )
        sys.exit(2)

    print(f"API Key  : {_redact(API_KEY)}")
    print(f"Base URL : {BASE_URL}")
    print(f"Model    : {MODEL_NAME}")
    print("=" * 60)

    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": "你好，请回复'测试成功'"}],
        "temperature": 0.7,
        "max_tokens": 100,
    }

    print(f"\n[POST] {url}")
    print(f"[payload] {json.dumps(payload, ensure_ascii=False)}")
    print("等待响应...\n")

    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)

        print(f"[status] {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print("[OK] API 调用成功")
            choices = data.get("choices") or []
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                print(f"[reply] {content}")
            else:
                print("[WARN] 响应格式不符合预期")
        else:
            print(f"[FAIL] HTTP {response.status_code}")
            print(f"[body] {response.text}")
            try:
                err = response.json().get("error")
                if err:
                    print(f"[error] {err}")
            except Exception:
                pass
    except httpx.TimeoutException:
        print("[FAIL] 请求超时，请检查网络。")
    except httpx.ConnectError:
        print("[FAIL] 连接失败，请检查网络/URL。")
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    test_dashscope_api()
