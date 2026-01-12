"""
依赖注入 - Dependency Injection

提供可复用的依赖注入函数，用于 FastAPI 路由。
"""

from typing import Generator
from fastapi import Depends, HTTPException, status
from adapters.cache_adapter import CacheAdapter
from adapters.llm_adapter import get_llm_adapter, BaseLLMAdapter
from services.reply_service import ReplyService
from services.user_service import UserService
from services.prompt_service import PromptService
from services.safety_service import SafetyService
from core.logger import logger


# ==================== Adapter 依赖 ====================

def get_cache_adapter() -> CacheAdapter:
    """获取 Redis 缓存适配器"""
    try:
        return CacheAdapter()
    except Exception as e:
        logger.error(f"Failed to initialize CacheAdapter: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable"
        )


def get_llm_adapter_dep() -> BaseLLMAdapter:
    """获取 LLM 适配器（工厂模式）"""
    try:
        return get_llm_adapter()
    except Exception as e:
        logger.error(f"Failed to initialize LLM adapter: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM service unavailable"
        )


# ==================== Service 依赖 ====================

def get_reply_service(
    llm_adapter: BaseLLMAdapter = Depends(get_llm_adapter_dep),
) -> ReplyService:
    """获取回复生成服务"""
    # ReplyService 内部会自动初始化其他依赖
    return ReplyService()


def get_user_service(
    cache_adapter: CacheAdapter = Depends(get_cache_adapter),
) -> UserService:
    """获取用户服务"""
    return UserService()


def get_prompt_service() -> PromptService:
    """获取 Prompt 服务"""
    return PromptService()


def get_safety_service() -> SafetyService:
    """获取安全检测服务"""
    return SafetyService()


# ==================== 认证与授权（Phase 2+ 使用）====================

async def get_current_user_id(
    # 这里可以从 Header 或 Cookie 中提取 user_id
    # 目前简化处理，直接从请求中获取
) -> str:
    """
    获取当前用户 ID（设备 ID）
    
    Phase 1: 简化版，直接从请求参数获取
    Phase 2+: 从 JWT Token 或 Cookie 中提取
    """
    # TODO: Phase 2+ 实现 JWT 认证
    return "anonymous"


__all__ = [
    "get_cache_adapter",
    "get_llm_adapter_dep",
    "get_reply_service",
    "get_user_service",
    "get_prompt_service",
    "get_safety_service",
    "get_current_user_id",
]
