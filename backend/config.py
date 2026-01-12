"""
全局配置管理

使用 Pydantic Settings 管理环境变量和配置。
"""

from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
from core.enums import LLMBackend


class Settings(BaseSettings):
    """应用配置"""
    
    # ==================== LLM 配置 ====================
    LLM_BACKEND: LLMBackend = LLMBackend.MOCK
    
    # DashScope (阿里云通义千问)
    DASHSCOPE_API_KEY: str = ""
    DASHSCOPE_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    DASHSCOPE_MODEL_NAME: str = "qwen-plus"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"
    
    # vLLM (自训练模型)
    VLLM_BASE_URL: Optional[str] = None
    VLLM_MODEL_PATH: Optional[str] = None
    
    # Ollama (本地部署)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5:7b"
    
    # ==================== Redis 配置 ====================
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_TTL: int = 3600  # 缓存过期时间（秒）
    
    # ==================== 应用配置 ====================
    ENVIRONMENT: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    
    # ==================== Prompt 配置 ====================
    PROMPT_TEMPLATE_VERSION: str = "v1"
    PROMPT_CACHE_TTL: int = 3600
    
    # ==================== 安全配置 ====================
    SAFETY_KEYWORDS_VERSION: str = "v1"
    SAFETY_STRICT_MODE: bool = False
    
    # ==================== 路径配置 ====================
    BASE_DIR: Path = Path(__file__).parent
    DATA_DIR: Path = BASE_DIR / "data"
    PROMPTS_DIR: Path = DATA_DIR / "prompts"
    RULES_DIR: Path = DATA_DIR / "rules"
    
    # ==================== 训练配置（Phase 4，暂时不用）====================
    TRAINING_DATA_SIZE: int = 5000
    TRAINING_DPO_SIZE: int = 2000
    TRAINING_GPT4_API_KEY: str = ""
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略额外的环境变量
    
    def get_cors_origins(self) -> list[str]:
        """获取 CORS 允许的源列表。

        说明：
        - Electron Desktop 通过 `file://` 加载页面时，浏览器侧会发送 `Origin: null`
        - 若后端未允许该 Origin，则渲染进程里的 fetch 会被 CORS 阻断，表现为 “API 未连接/一直识别中”
        """
        origins = [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        if "null" not in origins:
            origins.append("null")
        return origins
    
    def get_llm_config(self) -> dict:
        """获取当前 LLM 后端的配置"""
        if self.LLM_BACKEND == LLMBackend.DASHSCOPE:
            return {
                "api_key": self.DASHSCOPE_API_KEY,
                "base_url": self.DASHSCOPE_BASE_URL,
                "model_name": self.DASHSCOPE_MODEL_NAME,
            }
        elif self.LLM_BACKEND == LLMBackend.GPT4:
            return {
                "api_key": self.OPENAI_API_KEY,
                "base_url": self.OPENAI_BASE_URL,
                "model_name": self.OPENAI_MODEL_NAME,
            }
        elif self.LLM_BACKEND == LLMBackend.QWEN:
            return {
                "base_url": self.OLLAMA_BASE_URL,
                "model_name": self.OLLAMA_MODEL,
            }
        elif self.LLM_BACKEND == LLMBackend.FINETUNED:
            return {
                "base_url": self.VLLM_BASE_URL,
                "model_path": self.VLLM_MODEL_PATH,
            }
        else:  # MOCK
            return {}


# 全局配置实例
settings = Settings()


__all__ = ["settings", "Settings"]
