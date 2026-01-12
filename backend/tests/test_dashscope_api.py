#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 DashScope API Key 是否有效
"""

import httpx
import json
import sys

# 确保输出使用 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_KEY = "REDACTED-DASHSCOPE-KEY"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME = "qwen-plus"

def test_dashscope_api():
    """测试 DashScope API"""
    print("=" * 60)
    print("🧪 测试 DashScope API Key")
    print("=" * 60)
    print(f"📝 API Key: {API_KEY[:20]}...{API_KEY[-10:]}")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"🤖 Model: {MODEL_NAME}")
    print("=" * 60)
    
    url = f"{BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": "你好，请回复'测试成功'"}
        ],
        "temperature": 0.7,
        "max_tokens": 100,
    }
    
    print(f"\n📤 发送请求到: {url}")
    print(f"📦 Payload: {json.dumps(payload, ensure_ascii=False, indent=2)}")
    print("\n⏳ 等待响应...\n")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
            
            print(f"📊 状态码: {response.status_code}")
            print(f"📨 响应头:\n{json.dumps(dict(response.headers), ensure_ascii=False, indent=2)}\n")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API 调用成功!")
                print(f"📝 完整响应:\n{json.dumps(data, ensure_ascii=False, indent=2)}\n")
                
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    print(f"💬 AI 回复: {content}")
                    print("\n🎉 DashScope API Key 有效！")
                else:
                    print("⚠️ 响应格式不符合预期")
            else:
                print(f"❌ API 调用失败!")
                print(f"📝 错误响应:\n{response.text}\n")
                
                # 尝试解析错误信息
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        print(f"🚨 错误详情: {error_data['error']}")
                except:
                    pass
                    
    except httpx.TimeoutException:
        print("❌ 请求超时！请检查网络连接。")
    except httpx.ConnectError:
        print("❌ 连接失败！请检查网络连接或 URL 是否正确。")
    except Exception as e:
        print(f"❌ 发生未知错误: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_dashscope_api()
