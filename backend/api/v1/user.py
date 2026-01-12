"""
User API - 用户管理接口

负责用户画像（MBTI）的管理
"""

from fastapi import APIRouter, HTTPException
from schemas.request import UserProfileRequest, UserProfileGetRequest
from schemas.response import UserProfileResponse
from services.user_service import UserService
from core.logger import logger

router = APIRouter()


@router.post("/profile", response_model=UserProfileResponse)
async def update_user_profile(request: UserProfileRequest):
    """
    更新用户画像（MBTI）
    
    - **user_id**: 用户ID（设备ID）
    - **mbti**: MBTI 类型
    """
    try:
        user_service = UserService()
        profile = await user_service.update_user_profile(
            user_id=request.user_id,
            mbti=request.mbti
        )
        
        return UserProfileResponse(
            user_id=profile.user_id,
            mbti=profile.mbti,
            created_at=None,
            updated_at=None
        )
        
    except Exception as e:
        logger.error(f"❌ Update user profile failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"更新用户画像失败: {str(e)}"
        )


@router.get("/profile/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: str):
    """
    获取用户画像
    
    - **user_id**: 用户ID（设备ID）
    """
    try:
        user_service = UserService()
        profile = await user_service.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"用户画像不存在: {user_id}"
            )
        
        return UserProfileResponse(
            user_id=profile.user_id,
            mbti=profile.mbti,
            created_at=None,
            updated_at=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get user profile failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"获取用户画像失败: {str(e)}"
        )
