"""
API 响应数据模型

定义所有 API 响应的数据结构（Pydantic）。
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from core.enums import ReplyStyle, RiskLevel, RiskType, MBTIType


class ReplyOption(BaseModel):
    """单条回复选项"""
    
    content: str = Field(..., description="回复内容")
    style: ReplyStyle = Field(..., description="风格标签")
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "老板，收到。为了确保方案的质量和深度，我建议在周一上午精力最集中的时候处理。周末仓促赶工可能会影响决策质量。周一中午前我会给您一份详尽的方案。",
                "style": "mature",
                "confidence": 0.92
            }
        }


class RiskWarning(BaseModel):
    """风险预警"""
    
    level: RiskLevel = Field(..., description="风险等级")
    type: RiskType = Field(..., description="风险类型")
    reason: str = Field(..., description="风险原因")
    keywords: List[str] = Field(default_factory=list, description="触发的关键词")
    suggestion: Optional[str] = Field(None, description="建议")
    
    class Config:
        json_schema_extra = {
            "example": {
                "level": "high",
                "type": "pua",
                "reason": "对方使用了典型的PUA话术，包含贬低和控制意图",
                "keywords": ["你这种条件", "算你运气好"],
                "suggestion": "建议保持距离，这是明显的情感操控行为"
            }
        }


class ReplyGenerateResponse(BaseModel):
    """回复生成响应"""
    
    replies: List[ReplyOption] = Field(..., description="生成的回复选项（3条）")
    risk_warning: Optional[RiskWarning] = Field(None, description="风险预警（如有）")
    request_id: str = Field(..., description="请求ID（用于追踪）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "replies": [
                    {
                        "content": "老板，收到。为了确保方案质量，我建议周一处理。",
                        "style": "mature",
                        "confidence": 0.92
                    },
                    {
                        "content": "好的，我会尽快处理。不过为了保证效果，可能需要周一再给您。",
                        "style": "gentle",
                        "confidence": 0.88
                    },
                    {
                        "content": "明白了。周末时间有限，周一会给您一个更完善的方案。",
                        "style": "firm",
                        "confidence": 0.85
                    }
                ],
                "risk_warning": None,
                "request_id": "req-20260110-123456"
            }
        }


class DialogueMessage(BaseModel):
    """对话消息"""
    
    speaker: str = Field(..., description="说话人（'我' 或 '对方' 或具体名字）")
    content: str = Field(..., description="消息内容")
    
    class Config:
        json_schema_extra = {
            "example": {
                "speaker": "对方",
                "content": "小王，周末能加个班吗？"
            }
        }


class AnalysisResult(BaseModel):
    """分析结果"""
    
    scenario: str = Field(..., description="识别的场景")
    intent: str = Field(..., description="识别的意图")
    confidence: float = Field(..., description="置信度", ge=0.0, le=1.0)
    
    class Config:
        json_schema_extra = {
            "example": {
                "scenario": "workplace",
                "intent": "refuse",
                "confidence": 0.88
            }
        }


class ReplyAnalysisResponse(BaseModel):
    """截图智能识别响应"""
    
    extracted_dialogue: List[DialogueMessage] = Field(..., description="提取的对话")
    analysis: AnalysisResult = Field(..., description="智能分析结果")
    risk_warning: Optional[RiskWarning] = Field(None, description="风险预警（如有）")
    replies: List[ReplyOption] = Field(..., description="生成的回复选项（3条）")
    request_id: str = Field(..., description="请求ID（用于追踪）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "extracted_dialogue": [
                    {"speaker": "对方", "content": "小王，周末能加个班吗？"},
                    {"speaker": "我", "content": "好的，没问题。"},
                    {"speaker": "对方", "content": "周一要用，辛苦了。"}
                ],
                "analysis": {
                    "scenario": "workplace",
                    "intent": "refuse",
                    "confidence": 0.88
                },
                "risk_warning": None,
                "replies": [
                    {
                        "content": "老板，收到。为了确保方案质量，我建议周一处理。",
                        "style": "mature",
                        "confidence": 0.92
                    }
                ],
                "request_id": "req-20260110-123456"
            }
        }


class UserProfileResponse(BaseModel):
    """用户画像响应"""
    
    user_id: str = Field(..., description="用户ID")
    mbti: MBTIType = Field(..., description="用户MBTI类型")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "device-uuid-12345",
                "mbti": "INTJ",
                "created_at": "2026-01-10T12:00:00Z",
                "updated_at": "2026-01-10T12:00:00Z"
            }
        }


class HealthCheckResponse(BaseModel):
    """健康检查响应"""
    
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="服务版本")
    timestamp: str = Field(..., description="当前时间戳")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "version": "0.1.0",
                "timestamp": "2026-01-10T12:00:00Z"
            }
        }


class ErrorResponse(BaseModel):
    """错误响应"""
    
    code: str = Field(..., description="错误代码")
    message: str = Field(..., description="错误信息")
    detail: Optional[str] = Field(None, description="详细信息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "INVALID_MBTI",
                "message": "无效的MBTI类型",
                "detail": "有效类型: INTJ, INFJ, ISTJ, ..."
            }
        }


__all__ = [
    "ReplyOption",
    "RiskWarning",
    "ReplyGenerateResponse",
    "DialogueMessage",
    "AnalysisResult",
    "ReplyAnalysisResponse",
    "UserProfileResponse",
    "HealthCheckResponse",
    "ErrorResponse",
]
