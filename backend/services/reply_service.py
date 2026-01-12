"""
Reply Service - 回复生成服务

核心业务编排：风险检测 → Prompt构建 → LLM调用 → 后处理
"""

import json
import uuid
from typing import List
from core.logger import logger
from core.enums import ReplyStyle
from schemas.domain import DialogueContext, GeneratedReply, SafetyCheckResult
from schemas.response import ReplyOption, RiskWarning, ReplyGenerateResponse
from services.safety_service import SafetyService
from services.prompt_service import PromptService
from adapters.llm_adapter import get_llm_adapter


class ReplyService:
    """回复生成服务"""
    
    def __init__(self):
        self.safety_service = SafetyService()
        self.prompt_service = PromptService()
        self.llm_adapter = get_llm_adapter()
    
    async def generate_replies(self, context: DialogueContext) -> ReplyGenerateResponse:
        """
        生成回复
        
        Args:
            context: 对话上下文
            
        Returns:
            回复生成响应
        """
        request_id = f"req-{uuid.uuid4().hex[:12]}"
        logger.info(f"🚀 ReplyService: Starting reply generation, request_id={request_id}")
        logger.info(f"📊 Context: MBTI={context.mbti}, Scenario={context.scenario}, Intent={context.intent}")
        logger.info(f"💬 Dialogue: {context.dialogue[:100]}...")
        
        # Step 1: 安全检测
        logger.info(f"🔍 Step 1: Running safety check...")
        safety_result = self.safety_service.check_safety(context.dialogue)
        risk_warning = self._build_risk_warning(safety_result) if not safety_result.is_safe else None
        if risk_warning:
            logger.warning(f"⚠️ Risk detected: {risk_warning.level} - {risk_warning.reason}")
        else:
            logger.info(f"✅ Safety check passed")
        
        # Step 2: 构建 Prompt
        logger.info(f"📝 Step 2: Building prompt...")
        prompt = self.prompt_service.build_prompt(
            dialogue=context.dialogue,
            mbti=context.mbti,
            scenario=context.scenario,
            intent=context.intent,
            context=context.context
        )
        logger.debug(f"✅ Prompt built: {len(prompt)} characters")
        
        # Step 3: 调用 LLM
        logger.info(f"🤖 Step 3: Calling LLM adapter...")
        try:
            raw_replies = await self.llm_adapter.generate(prompt, n=3)
            logger.info(f"✅ LLM returned {len(raw_replies)} raw replies")
            replies = self._parse_replies(raw_replies)
            logger.info(f"✅ Parsed {len(replies)} valid replies")
        except Exception as e:
            logger.exception(f"❌ LLM generation failed: {e}")
            # 降级：返回默认回复
            logger.warning(f"⚠️ Falling back to default replies")
            replies = self._get_fallback_replies()
        
        # Step 4: 构建响应
        logger.info(f"📦 Step 4: Building response...")
        response = ReplyGenerateResponse(
            replies=replies,
            risk_warning=risk_warning,
            request_id=request_id
        )
        
        logger.info(f"✅ Reply generation completed, request_id={request_id}, total_replies={len(replies)}")
        return response
    
    def _build_risk_warning(self, safety_result: SafetyCheckResult) -> RiskWarning:
        """构建风险预警"""
        return RiskWarning(
            level=safety_result.risk_level,
            type=safety_result.risk_type,
            reason=safety_result.reason,
            keywords=safety_result.keywords,
            suggestion=safety_result.suggestion
        )
    
    def _parse_replies(self, raw_replies: List[str]) -> List[ReplyOption]:
        """
        解析 LLM 返回的回复
        
        Args:
            raw_replies: LLM 原始回复
            
        Returns:
            解析后的回复选项列表
        """
        parsed_replies = []
        
        for raw_reply in raw_replies:
            try:
                # 尝试解析 JSON 格式
                if raw_reply.strip().startswith("["):
                    # JSON 数组格式
                    data = json.loads(raw_reply)
                    for item in data:
                        parsed_replies.append(ReplyOption(
                            content=item.get("content", ""),
                            style=ReplyStyle(item.get("style", "mature")),
                            confidence=float(item.get("confidence", 0.8))
                        ))
                else:
                    # 纯文本格式，使用默认值
                    parsed_replies.append(ReplyOption(
                        content=raw_reply.strip(),
                        style=ReplyStyle.MATURE,
                        confidence=0.85
                    ))
            except Exception as e:
                logger.warning(f"⚠️ Failed to parse reply: {e}, using as plain text")
                parsed_replies.append(ReplyOption(
                    content=raw_reply.strip(),
                    style=ReplyStyle.MATURE,
                    confidence=0.80
                ))
        
        # 确保返回至少3条回复
        while len(parsed_replies) < 3:
            parsed_replies.extend(self._get_fallback_replies())
        
        return parsed_replies[:3]
    
    def _get_fallback_replies(self) -> List[ReplyOption]:
        """获取降级回复（当 LLM 调用失败时）"""
        return [
            ReplyOption(
                content="收到，我会认真考虑您的建议。为了给您一个更好的回复，我需要一些时间整理思路。",
                style=ReplyStyle.MATURE,
                confidence=0.75
            ),
            ReplyOption(
                content="好的，我理解您的意思。让我想想怎么回应会更合适。",
                style=ReplyStyle.GENTLE,
                confidence=0.70
            ),
            ReplyOption(
                content="明白了。我会好好思考这个问题，稍后给您回复。",
                style=ReplyStyle.RATIONAL,
                confidence=0.70
            )
        ]


__all__ = ["ReplyService"]
