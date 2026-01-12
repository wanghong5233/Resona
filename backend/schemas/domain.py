"""
领域模型

定义业务逻辑中使用的领域模型（复用枚举和类型）。
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from core.enums import MBTIType, ScenarioType, IntentType, ReplyStyle, RiskLevel, RiskType


class UserProfile(BaseModel):
    """用户画像（领域模型）"""
    
    user_id: str
    mbti: MBTIType
    preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="用户偏好设置")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "device-uuid-12345",
                "mbti": "INTJ",
                "preferences": {
                    "default_scenario": "workplace",
                    "preferred_style": "mature"
                }
            }
        }


class DialogueContext(BaseModel):
    """对话上下文（领域模型）"""
    
    dialogue: str
    mbti: MBTIType
    scenario: ScenarioType
    intent: IntentType
    context: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "dialogue": "周五下班前老板突然要求改方案",
                "mbti": "INTJ",
                "scenario": "workplace",
                "intent": "refuse",
                "context": "非紧急需求"
            }
        }


class GeneratedReply(BaseModel):
    """生成的回复（领域模型）"""
    
    content: str
    style: ReplyStyle
    confidence: float
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "老板，收到。为了确保方案质量...",
                "style": "mature",
                "confidence": 0.92,
                "metadata": {
                    "model": "gpt4",
                    "tokens": 150
                }
            }
        }


class SafetyCheckResult(BaseModel):
    """安全检测结果（领域模型）"""
    
    is_safe: bool
    risk_level: RiskLevel
    risk_type: RiskType
    reason: str
    keywords: List[str] = Field(default_factory=list)
    suggestion: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "is_safe": False,
                "risk_level": "high",
                "risk_type": "pua",
                "reason": "检测到PUA话术",
                "keywords": ["你这种条件"],
                "suggestion": "建议保持距离"
            }
        }


__all__ = [
    "UserProfile",
    "DialogueContext",
    "GeneratedReply",
    "SafetyCheckResult",
]
