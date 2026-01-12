"""
Cache Adapter - Redis 缓存适配器

提供统一的缓存操作接口。
"""

import json
from typing import Optional, Any
import redis.asyncio as aioredis
from redis.asyncio import Redis
from core.logger import logger
from core.exceptions import CacheError
from config import settings


class CacheAdapter:
    """Redis 缓存适配器"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
        self.ttl = settings.REDIS_TTL
    
    async def connect(self):
        """连接 Redis"""
        try:
            self.redis = await aioredis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}",
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                encoding="utf-8",
                decode_responses=True
            )
            # 测试连接
            await self.redis.ping()
            logger.info(f"✅ Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise CacheError(f"Redis 连接失败: {e}")
    
    async def disconnect(self):
        """断开 Redis 连接"""
        if self.redis:
            await self.redis.close()
            logger.info("👋 Redis disconnected")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，不存在返回 None
        """
        if not self.redis:
            await self.connect()
        
        try:
            value = await self.redis.get(key)
            if value:
                logger.debug(f"📦 Cache hit: {key}")
                return json.loads(value)
            else:
                logger.debug(f"❌ Cache miss: {key}")
                return None
        except Exception as e:
            logger.error(f"❌ Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 则使用默认值
            
        Returns:
            是否成功
        """
        if not self.redis:
            await self.connect()
        
        try:
            ttl = ttl or self.ttl
            value_str = json.dumps(value, ensure_ascii=False)
            await self.redis.setex(key, ttl, value_str)
            logger.debug(f"💾 Cache set: {key} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功
        """
        if not self.redis:
            await self.connect()
        
        try:
            await self.redis.delete(key)
            logger.debug(f"🗑️ Cache deleted: {key}")
            return True
        except Exception as e:
            logger.error(f"❌ Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
            
        Returns:
            是否存在
        """
        if not self.redis:
            await self.connect()
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"❌ Cache exists error: {e}")
            return False


# 全局缓存实例
_cache_adapter: Optional[CacheAdapter] = None


async def get_cache_adapter() -> CacheAdapter:
    """获取缓存适配器实例（单例）"""
    global _cache_adapter
    if _cache_adapter is None:
        _cache_adapter = CacheAdapter()
        await _cache_adapter.connect()
    return _cache_adapter


__all__ = ["CacheAdapter", "get_cache_adapter"]
