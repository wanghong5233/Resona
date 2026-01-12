"""
Reply API - 回复生成接口

核心功能：生成高情商回复
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Form
from schemas.request import ReplyGenerateRequest
from schemas.response import ReplyGenerateResponse, ReplyAnalysisResponse, DialogueMessage, RiskWarning
from schemas.domain import DialogueContext
from services.reply_service import ReplyService
from services.ocr_service import OCRService
from services.analysis_service import AnalysisService
from services.safety_service import SafetyService
from core.logger import logger
from core.enums import MBTIType
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/generate", response_model=ReplyGenerateResponse)
async def generate_reply(request: ReplyGenerateRequest):
    """
    生成高情商回复
    
    - **dialogue**: 原始对话内容
    - **mbti**: 用户MBTI类型
    - **scenario**: 场景类型（workplace/intimate/family/social）
    - **intent**: 意图类型（refuse/apologize/request/boundary/comfort等）
    - **context**: 额外上下文（可选）
    
    返回3条候选回复 + 风险预警（如有）
    """
    logger.info(f"📨 Received reply generation request")
    logger.debug(f"📋 Request details: MBTI={request.mbti}, Scenario={request.scenario}, Intent={request.intent}")
    
    try:
        # 构建对话上下文
        context = DialogueContext(
            dialogue=request.dialogue,
            mbti=request.mbti,
            scenario=request.scenario,
            intent=request.intent,
            context=request.context
        )
        
        # 调用服务层
        reply_service = ReplyService()
        response = await reply_service.generate_replies(context)
        
        logger.info(f"✅ Reply generation successful, returning {len(response.replies)} replies")
        return response
        
    except Exception as e:
        logger.exception(f"❌ Reply generation API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"回复生成失败: {str(e)}"
        )


@router.post("/analyze-from-image", response_model=ReplyAnalysisResponse)
async def analyze_from_image(
    image: UploadFile = File(..., description="聊天截图"),
    mbti: MBTIType = Form(..., description="用户 MBTI 类型")
):
    """
    从截图智能识别对话并生成回复
    
    流程：
    1. OCR 提取对话
    2. 智能识别场景和意图
    3. 风险检测
    4. 生成 MBTI 风格回复
    
    - **image**: 聊天截图文件（PNG/JPEG）
    - **mbti**: 用户 MBTI 类型
    
    返回：提取的对话 + 分析结果 + 风险预警
    （注意：此接口**不**直接生成回复，避免 OCR 阶段就消耗 LLM）
    """
    request_id = f"req-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:6]}"
    logger.info(f"📸 [req={request_id}] Received screenshot analysis request")
    logger.debug(f"📋 [req={request_id}] MBTI={mbti}, filename={image.filename}")
    
    try:
        # 1. 读取图片
        image_bytes = await image.read()
        logger.info(f"📥 [req={request_id}] Image uploaded, size={len(image_bytes)} bytes")
        
        # 2. OCR 提取对话
        ocr_service = OCRService()
        dialogue_list = await ocr_service.extract_dialogue_from_image(image_bytes)
        
        if not dialogue_list:
            logger.warning(f"⚠️ [req={request_id}] No dialogue extracted from image")
            raise HTTPException(
                status_code=400,
                detail="无法从截图中识别出对话，请确保截图清晰且包含聊天内容"
            )
        
        # 3. 拼接对话文本
        dialogue_text = "\n".join([
            f"{msg['speaker']}: {msg['content']}" 
            for msg in dialogue_list
        ])
        logger.info(f"📝 [req={request_id}] Dialogue extracted: {len(dialogue_list)} messages")
        
        # 4. 智能识别场景和意图
        analysis_service = AnalysisService()
        scenario, intent, confidence = analysis_service.analyze_dialogue(dialogue_text)
        logger.info(
            f"🔍 [req={request_id}] Analysis: scenario={scenario}, "
            f"intent={intent}, confidence={confidence:.2f}"
        )
        
        # 5. 风险检测（关键词规则，快速）
        safety_service = SafetyService()
        safety_result = safety_service.check_safety(dialogue_text)
        risk_warning = None
        if not safety_result.is_safe:
            risk_warning = RiskWarning(
                level=safety_result.risk_level,
                type=safety_result.risk_type,
                reason=safety_result.reason,
                keywords=safety_result.keywords,
                suggestion=safety_result.suggestion,
            )
        
        # 7. 构建响应
        response = ReplyAnalysisResponse(
            extracted_dialogue=[
                DialogueMessage(speaker=msg["speaker"], content=msg["content"])
                for msg in dialogue_list
            ],
            analysis={
                "scenario": scenario,
                "intent": intent,
                "confidence": confidence
            },
            risk_warning=risk_warning,
            replies=[],
            request_id=request_id
        )
        
        logger.info(
            f"✅ [req={request_id}] Screenshot analysis complete, "
            f"returning {len(response.replies)} replies"
        )
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"❌ [req={request_id}] Screenshot analysis API error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"截图分析失败: {str(e)}"
        )
