"""
API 请求数据模型

定义所有 API 请求的数据结构（Pydantic）。
"""

from pydantic import BaseModel, Field
from typing import Optional
from core.enums import MBTIType, ScenarioType, IntentType


class ReplyGenerateRequest(BaseModel):
    """回复生成请求"""
    
    dialogue: str = Field(..., description="原始对话内容", min_length=1, max_length=5000)
    mbti: MBTIType = Field(..., description="用户MBTI类型")
    scenario: ScenarioType = Field(..., description="场景类型")
    intent: IntentType = Field(..., description="意图类型")
    context: Optional[str] = Field(None, description="额外上下文信息", max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "dialogue": "周五下班前老板突然要求改方案，说周一要用。",
                "mbti": "INTJ",
                "scenario": "workplace",
                "intent": "refuse",
                "context": "这是一个非紧急的需求，可以延后处理"
            }
        }


class UserProfileRequest(BaseModel):
    """用户画像请求"""
    
    user_id: str = Field(..., description="用户ID（设备ID）", min_length=1, max_length=100)
    mbti: MBTIType = Field(..., description="用户MBTI类型")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "device-uuid-12345",
                "mbti": "INTJ"
            }
        }


class UserProfileGetRequest(BaseModel):
    """获取用户画像请求"""
    
    user_id: str = Field(..., description="用户ID（设备ID）", min_length=1, max_length=100)
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "device-uuid-12345"
            }
        }


__all__ = [
    "ReplyGenerateRequest",
    "UserProfileRequest",
    "UserProfileGetRequest",
]
