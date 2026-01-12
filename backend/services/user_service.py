"""
User Service - 用户服务

负责用户画像管理（存储到 Redis）。
"""

from typing import Optional
from core.logger import logger
from core.enums import MBTIType
from schemas.domain import UserProfile
from adapters.cache_adapter import get_cache_adapter


class UserService:
    """用户服务"""
    
    def __init__(self):
        self.cache = None
    
    async def _get_cache(self):
        """获取缓存实例"""
        if self.cache is None:
            self.cache = await get_cache_adapter()
        return self.cache
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        获取用户画像
        
        Args:
            user_id: 用户ID
            
        Returns:
            用户画像，不存在返回 None
        """
        cache = await self._get_cache()
        cache_key = f"user:profile:{user_id}"
        
        data = await cache.get(cache_key)
        if data:
            logger.info(f"👤 User profile found: {user_id}")
            return UserProfile(**data)
        else:
            logger.info(f"❌ User profile not found: {user_id}")
            return None
    
    async def update_user_profile(self, user_id: str, mbti: MBTIType) -> UserProfile:
        """
        更新用户画像
        
        Args:
            user_id: 用户ID
            mbti: MBTI 类型
            
        Returns:
            更新后的用户画像
        """
        cache = await self._get_cache()
        cache_key = f"user:profile:{user_id}"
        
        profile = UserProfile(user_id=user_id, mbti=mbti)
        
        await cache.set(cache_key, profile.model_dump(), ttl=86400 * 30)  # 30天
        logger.info(f"✅ User profile updated: {user_id} - MBTI: {mbti}")
        
        return profile


__all__ = ["UserService"]
