"""
LLM Adapter - LLM 调用适配器

支持多种 LLM 后端：Mock, GPT-4, DashScope, Qwen, Fine-tuned
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
import json
from core.logger import logger
from core.exceptions import LLMServiceError
from config import settings


class BaseLLMAdapter(ABC):
    """LLM 适配器基类"""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        n: int = 3,
        **kwargs
    ) -> List[str]:
        """
        生成回复
        
        Args:
            prompt: 输入 Prompt
            temperature: 温度参数（0-1）
            max_tokens: 最大生成 token 数
            n: 生成数量
            **kwargs: 其他参数
            
        Returns:
            生成的回复列表
        """
        pass


class MockLLMAdapter(BaseLLMAdapter):
    """Mock LLM 适配器（用于测试）"""
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        n: int = 3,
        **kwargs
    ) -> List[str]:
        """返回预设的 Mock 回复"""
        logger.info("🎭 MockLLMAdapter: Generating mock replies")
        
        # 返回3条预设回复
        return [
            "老板，收到。为了确保方案的质量和深度，我建议在周一上午精力最集中的时候处理。周末仓促赶工可能会影响决策质量。周一中午前我会给您一份详尽的方案。",
            "好的，我会尽快处理。不过为了保证效果，可能需要周一再给您。这样可以确保方案的完整性。",
            "明白了。周末时间有限，周一会给您一个更完善的方案。谢谢理解！"
        ][:n]


class DashScopeAdapter(BaseLLMAdapter):
    """阿里云通义千问适配器"""
    
    def __init__(self):
        self.api_key = settings.DASHSCOPE_API_KEY
        self.base_url = settings.DASHSCOPE_BASE_URL
        self.model_name = settings.DASHSCOPE_MODEL_NAME
        
        if not self.api_key:
            raise LLMServiceError("DashScope API Key 未配置", provider="dashscope")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        n: int = 3,
        **kwargs
    ) -> List[str]:
        """调用 DashScope API"""
        logger.info(f"🤖 DashScopeAdapter: Calling {self.model_name}")
        logger.debug(f"📝 Prompt preview: {prompt[:200]}...")
        logger.debug(f"⚙️ Parameters: temperature={temperature}, max_tokens={max_tokens}, n={n}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                request_payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "n": n,
                }
                logger.debug(f"📤 Request URL: {self.base_url}/chat/completions")
                logger.debug(f"🔑 API Key: {self.api_key[:20]}...{self.api_key[-4:]}")
                
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=request_payload
                )
                response.raise_for_status()
                
                data = response.json()
                replies = [choice["message"]["content"] for choice in data["choices"]]
                
                logger.info(f"✅ DashScope API success, generated {len(replies)} replies")
                for i, reply in enumerate(replies, 1):
                    logger.debug(f"📨 Reply {i} preview: {reply[:100]}...")
                return replies
                
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ DashScope API HTTP error: {e.response.status_code}")
                logger.error(f"❌ Response body: {e.response.text}")
                raise LLMServiceError(f"DashScope API 调用失败: {e}", provider="dashscope")
            except Exception as e:
                logger.exception(f"❌ DashScope API unexpected error: {e}")
                raise LLMServiceError(f"DashScope API 调用异常: {e}", provider="dashscope")


class GPTAdapter(BaseLLMAdapter):
    """OpenAI GPT 适配器"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL.rstrip("/")
        self.model_name = settings.OPENAI_MODEL_NAME
        
        if not self.api_key:
            raise LLMServiceError("OpenAI API Key 未配置", provider="openai")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        n: int = 3,
        **kwargs
    ) -> List[str]:
        """调用 OpenAI API"""
        logger.info(f"🤖 GPTAdapter: Calling {self.model_name}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "n": n,
                    }
                )
                response.raise_for_status()
                
                data = response.json()
                replies = [choice["message"]["content"] for choice in data["choices"]]
                
                logger.info(f"✅ OpenAI API success, generated {len(replies)} replies")
                return replies
                
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ OpenAI API error: {e.response.status_code} - {e.response.text}")
                raise LLMServiceError(f"OpenAI API 调用失败: {e}", provider="openai")
            except Exception as e:
                logger.error(f"❌ OpenAI API error: {e}")
                raise LLMServiceError(f"OpenAI API 调用异常: {e}", provider="openai")


class QwenAdapter(BaseLLMAdapter):
    """Ollama / Qwen 本地部署适配器"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.model_name = settings.OLLAMA_MODEL
        
        if not self.base_url or not self.model_name:
            raise LLMServiceError("Qwen/Ollama 配置缺失", provider="qwen")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        n: int = 3,
        **kwargs
    ) -> List[str]:
        """调用本地 Ollama Chat API"""
        logger.info(f"🤖 QwenAdapter: Calling {self.model_name}")
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are Resona, an MBTI-aligned high EQ assistant."},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                
                data = response.json()
                content = ""
                if "message" in data and isinstance(data["message"], dict):
                    content = data["message"].get("content", "")
                elif "messages" in data:
                    # 部分 Ollama 版本返回 messages 数组
                    content = "".join(msg.get("content", "") for msg in data["messages"])
                
                if not content:
                    raise LLMServiceError("QwenAdapter 未返回内容", provider="qwen")
                
                # 如果只返回一条回复，复制扩展到 n 条，保证上层逻辑稳定
                replies = [content]
                if "responses" in data:
                    replies = [resp.get("content", content) for resp in data["responses"] if resp.get("content")]
                
                if len(replies) < n:
                    ratio = (n + len(replies) - 1) // len(replies)
                    replies = (replies * ratio)[:n]
                else:
                    replies = replies[:n]
                
                logger.info(f"✅ Qwen/Ollama success, generated {len(replies)} replies")
                return replies
                
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ Qwen/Ollama HTTP error: {e.response.status_code} - {e.response.text}")
                raise LLMServiceError(f"Qwen/Ollama 调用失败: {e}", provider="qwen")
            except Exception as e:
                logger.error(f"❌ Qwen/Ollama error: {e}")
                raise LLMServiceError(f"Qwen/Ollama 调用异常: {e}", provider="qwen")


class VLLMAdapter(BaseLLMAdapter):
    """vLLM 自训练模型适配器（OpenAI 兼容协议）"""
    
    def __init__(self):
        self.base_url = settings.VLLM_BASE_URL.rstrip("/") if settings.VLLM_BASE_URL else None
        self.model_path = settings.VLLM_MODEL_PATH
        
        if not self.base_url or not self.model_path:
            raise LLMServiceError("vLLM 服务配置缺失", provider="finetuned")
    
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 500,
        n: int = 3,
        **kwargs
    ) -> List[str]:
        """调用 vLLM OpenAI-Compatible 接口"""
        logger.info(f"🤖 VLLMAdapter: Calling model path {self.model_path}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json={
                        "model": self.model_path,
                        "messages": [
                            {"role": "system", "content": "You are Resona, an MBTI-aligned high EQ assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "n": n,
                    },
                )
                response.raise_for_status()
                
                data = response.json()
                replies = [choice["message"]["content"] for choice in data.get("choices", [])]
                if not replies:
                    raise LLMServiceError("vLLM 未返回有效内容", provider="finetuned")
                
                logger.info(f"✅ vLLM success, generated {len(replies)} replies")
                return replies
                
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ vLLM HTTP error: {e.response.status_code} - {e.response.text}")
                raise LLMServiceError(f"vLLM 调用失败: {e}", provider="finetuned")
            except Exception as e:
                logger.error(f"❌ vLLM error: {e}")
                raise LLMServiceError(f"vLLM 调用异常: {e}", provider="finetuned")


def get_llm_adapter() -> BaseLLMAdapter:
    """
    根据配置获取 LLM 适配器实例
    
    Returns:
        LLM 适配器实例
    """
    from core.enums import LLMBackend
    
    backend = settings.LLM_BACKEND
    logger.info(f"🔧 Initializing LLM Adapter: {backend}")
    
    if backend == LLMBackend.MOCK:
        logger.info("✅ Using MockLLMAdapter")
        return MockLLMAdapter()
    elif backend == LLMBackend.DASHSCOPE:
        logger.info(f"✅ Using DashScopeAdapter with model: {settings.DASHSCOPE_MODEL_NAME}")
        return DashScopeAdapter()
    elif backend == LLMBackend.GPT4:
        logger.info(f"✅ Using GPTAdapter with model: {settings.OPENAI_MODEL_NAME}")
        return GPTAdapter()
    elif backend == LLMBackend.QWEN:
        logger.info(f"✅ Using QwenAdapter with model: {settings.OLLAMA_MODEL}")
        return QwenAdapter()
    elif backend == LLMBackend.FINETUNED:
        logger.info(f"✅ Using VLLMAdapter with model path: {settings.VLLM_MODEL_PATH}")
        return VLLMAdapter()
    else:
        logger.warning(f"⚠️ Unsupported LLM backend: {backend}, falling back to Mock")
        return MockLLMAdapter()


__all__ = [
    "BaseLLMAdapter",
    "MockLLMAdapter",
    "DashScopeAdapter",
    "GPTAdapter",
    "QwenAdapter",
    "VLLMAdapter",
    "get_llm_adapter",
]
