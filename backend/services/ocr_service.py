"""
OCR 识别服务

负责从聊天截图中提取对话内容
"""

from typing import Dict, List, Optional
from io import BytesIO
import re
import base64
import json

import httpx
from PIL import Image

from config import settings
from core.logger import logger


class OCRService:
    """OCR 识别服务（阿里云 DashScope）"""
    
    async def extract_dialogue_from_image(
        self, 
        image_bytes: bytes
    ) -> List[Dict[str, str]]:
        """
        从聊天截图中提取对话
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            [{"speaker": "对方", "content": "..."}, {"speaker": "我", "content": "..."}]
        """
        logger.info(f"📷 OCR: Processing image, size={len(image_bytes)} bytes")
        
        # 1. 图片预处理（压缩、裁剪边缘）
        processed_image = self._preprocess_image(image_bytes)

        # 2. 优先：让 VL 直接按“气泡左右”输出结构化 JSON（单聊：右侧=我，左侧=对方）
        try:
            structured = await self._call_dashscope_chat_dialogue(processed_image)
            dialogue = self._parse_vl_dialogue_json(structured)
            if dialogue:
                logger.info(f"✅ OCR: Extracted {len(dialogue)} messages (structured)")
                return dialogue
            logger.warning("⚠️ OCR: Structured extraction returned empty, falling back to plain OCR")
        except Exception as e:
            logger.warning(f"⚠️ OCR: Structured extraction failed, fallback to plain OCR: {e}")

        # 3. 降级：调用 DashScope OCR（纯文本）+ 旧解析（可能会错配连续同一说话人）
        raw_text = await self._call_dashscope_ocr(processed_image)
        dialogue = self._parse_chat_screenshot(raw_text)
        logger.info(f"✅ OCR: Extracted {len(dialogue)} messages (fallback)")
        return dialogue
    
    def _preprocess_image(self, image_bytes: bytes) -> bytes:
        """
        图片预处理：压缩、去噪
        
        Args:
            image_bytes: 原始图片二进制数据
            
        Returns:
            处理后的图片二进制数据
        """
        try:
            img = Image.open(BytesIO(image_bytes))
            
            # 限制尺寸（长边不超过 1600px）
            max_size = 1600
            if max(img.size) > max_size:
                ratio = max_size / max(img.size)
                new_size = (int(img.width * ratio), int(img.height * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                logger.info(f"🔧 OCR: Resized image to {new_size}")
            
            # 转为 RGB（避免 RGBA/灰度问题）
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 保存为 PNG
            output = BytesIO()
            img.save(output, format='PNG', optimize=True)
            processed_bytes = output.getvalue()
            
            logger.info(f"🔧 OCR: Preprocessed image, new size={len(processed_bytes)} bytes")
            return processed_bytes
            
        except Exception as e:
            logger.warning(f"⚠️ OCR: Preprocessing failed, using original: {e}")
            return image_bytes
    
    async def _call_dashscope_ocr(self, image_bytes: bytes) -> str:
        """
        调用阿里云 DashScope OCR API
        
        Args:
            image_bytes: 图片二进制数据
            
        Returns:
            识别的文本内容
        """
        # DashScope OCR API 文档:
        # https://help.aliyun.com/zh/model-studio/developer-reference/tongyi-qianwen-vl-api
        
        # 说明：
        # 这里复用 DashScope 的 OpenAI 兼容模式，走多模态模型做 OCR（MVP 可用）。
        # 如果后续要更稳定/更省钱，可替换为专用 OCR API（结构化返回）。
        url = f"{settings.DASHSCOPE_BASE_URL}/chat/completions"

        image_base64 = base64.b64encode(image_bytes).decode("utf-8")
        
        payload = {
            # 优先用更便宜的模型；如需更高质量可改为 qwen-vl-max
            "model": getattr(settings, "DASHSCOPE_VL_MODEL_NAME", None) or "qwen-vl-plus",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": "请识别图片中的所有文字内容。要求：尽量保持原始换行，不要额外解释。"
                        }
                    ]
                }
            ]
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                # 提取识别文本
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0]["message"]["content"]
                    logger.info(f"✅ OCR: Text extracted, length={len(text)}")
                    return text
                
                logger.warning("⚠️ OCR: No text extracted from response")
                return ""
                
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ OCR: HTTP error {e.response.status_code}: {e.response.text}")
            raise Exception(f"OCR API 调用失败: {e.response.status_code}")
        except Exception as e:
            logger.error(f"❌ OCR: Failed to call DashScope API: {e}")
            raise Exception(f"OCR 识别失败: {str(e)}")

    async def _call_dashscope_chat_dialogue(self, image_bytes: bytes) -> str:
        """让 VL 直接输出单聊对话的结构化 JSON（带 left/right）。"""
        url = f"{settings.DASHSCOPE_BASE_URL}/chat/completions"
        image_base64 = base64.b64encode(image_bytes).decode("utf-8")

        instruction = (
            "你将看到一张微信/QQ【单人聊天】截图。请提取聊天气泡中的文字，并判断每条消息属于谁。\n"
            "规则：右侧(通常为绿色气泡)=我，左侧(通常为白色气泡)=对方。\n"
            "要求：\n"
            "1) 只提取聊天气泡里的文字，忽略时间分割线/系统提示/昵称/头像/状态栏等。\n"
            "2) 按照从上到下的顺序输出。\n"
            "3) 输出【严格 JSON 数组】（不要 Markdown，不要额外解释）。\n"
            "4) 每个元素结构：{\"side\":\"left\"|\"right\",\"text\":\"...\"}\n"
            "5) 同一气泡若多行，请在 text 中用 \\n 保留换行。\n"
        )

        payload = {
            "model": getattr(settings, "DASHSCOPE_VL_MODEL_NAME", None) or "qwen-vl-plus",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            },
                        },
                        {"type": "text", "text": instruction},
                    ],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                headers={
                    "Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
            return ""

    def _parse_vl_dialogue_json(self, raw: str) -> List[Dict[str, str]]:
        """解析 VL 输出的 JSON 对话，并用 side → speaker 映射（单聊：right=我）。"""
        if not raw or not raw.strip():
            return []

        text = raw.strip()

        # 去掉可能的 code fence
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)

        # 尝试截取 JSON 数组主体
        m = re.search(r"\[[\s\S]*\]", text)
        if m:
            text = m.group(0)

        try:
            data = json.loads(text)
        except Exception as e:
            logger.warning(f"⚠️ OCR: Failed to parse structured JSON: {e}")
            return []

        if not isinstance(data, list):
            return []

        dialogue: List[Dict[str, str]] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            side = str(item.get("side", "")).strip().lower()
            content = item.get("text", item.get("content", ""))
            if content is None:
                continue
            content_str = str(content).strip()
            if not content_str:
                continue

            # 过滤时间分割线（模型偶尔会误提取）
            if self._looks_like_time_separator(content_str):
                continue

            if side not in ("left", "right"):
                # side 不可信就跳过（宁可降级，不要错配）
                continue

            speaker = "我" if side == "right" else "对方"
            dialogue.append({"speaker": speaker, "content": content_str})

        # 只保留最近 6 轮
        return dialogue[-6:]

    def _looks_like_time_separator(self, text: str) -> bool:
        """判断是否是时间分割线（如：昨天 17:48）。"""
        t = text.strip()
        # 常见：昨天 17:48 / 17:48 / 2026-01-12 17:48
        if self._is_timestamp(t):
            return True
        if re.search(r"(昨天|今天|上午|下午|晚上)\s*\d{1,2}:\d{2}", t):
            return True
        return False
    
    def _parse_chat_screenshot(self, raw_text: str) -> List[Dict[str, str]]:
        """
        解析聊天截图文本
        
        规则：
        1. 检测时间戳行（15:30、下午3:30、昨天 15:30）
        2. 时间戳前后识别说话人和内容
        3. 简单规则：交替识别"对方"和"我"
        
        Args:
            raw_text: OCR 识别的原始文本
            
        Returns:
            [{"speaker": "对方", "content": "..."}, ...]
        """
        if not raw_text or not raw_text.strip():
            return []
        
        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
        dialogue = []
        
        i = 0
        last_speaker = None
        
        while i < len(lines):
            line = lines[i]
            
            # 检测时间戳
            if self._is_timestamp(line):
                # 时间戳前一行可能是说话人
                speaker_name = lines[i-1] if i > 0 else None
                # 时间戳后一行是内容
                content = lines[i+1] if i+1 < len(lines) else None
                
                if content:
                    # 判断角色（启发式）
                    if speaker_name and any(kw in speaker_name for kw in ["我", "Me", "自己"]):
                        speaker = "我"
                    elif speaker_name and any(kw in speaker_name for kw in ["老板", "领导", "女朋友", "男朋友"]):
                        speaker = "对方"
                    else:
                        # 交替识别（简单规则）
                        speaker = "我" if last_speaker == "对方" else "对方"
                    
                    dialogue.append({
                        "speaker": speaker,
                        "content": content
                    })
                    last_speaker = speaker
                
                i += 2  # 跳过内容行
            else:
                i += 1
        
        # 如果没有识别出时间戳，尝试按行识别（降级）
        if not dialogue:
            logger.warning("⚠️ OCR: No timestamp detected, using fallback parsing")
            dialogue = self._parse_simple(lines)
        
        # 只保留最近 6 轮对话
        dialogue = dialogue[-6:]
        
        return dialogue
    
    def _parse_simple(self, lines: List[str]) -> List[Dict[str, str]]:
        """
        简单解析模式（降级方案）
        
        假设每行都是对话内容，交替分配"对方"和"我"
        """
        dialogue = []
        for i, line in enumerate(lines):
            if len(line) < 2:  # 跳过太短的行
                continue
            speaker = "我" if i % 2 == 1 else "对方"
            dialogue.append({
                "speaker": speaker,
                "content": line
            })
        return dialogue
    
    def _is_timestamp(self, text: str) -> bool:
        """
        判断是否为时间戳
        
        匹配格式：
        - 15:30
        - 下午3:30
        - 昨天 15:30
        - 2026-01-10 15:30
        """
        # 匹配 HH:MM 格式
        return bool(re.search(r'\d{1,2}:\d{2}', text))
