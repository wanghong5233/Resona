"""
Safety Service - 安全检测服务

基于关键词规则引擎检测 PUA、诈骗、情绪勒索等风险。
"""

from typing import List
from core.logger import logger
from core.enums import RiskLevel, RiskType
from schemas.domain import SafetyCheckResult
from adapters.config_adapter import ConfigAdapter


class SafetyService:
    """安全检测服务"""
    
    def __init__(self):
        self.config = ConfigAdapter()
        self.rules = self.config.load_safety_rules()
    
    def check_safety(self, dialogue: str) -> SafetyCheckResult:
        """
        检查对话安全性
        
        Args:
            dialogue: 对话内容
            
        Returns:
            安全检测结果
        """
        logger.info("🔍 SafetyService: Checking dialogue safety")
        
        # 检测各类风险
        pua_keywords = self._check_keywords(dialogue, self.rules["pua_keywords"])
        scam_keywords = self._check_keywords(dialogue, self.rules["scam_keywords"])
        emotional_blackmail_keywords = self._check_keywords(dialogue, self.rules["emotional_blackmail_keywords"])
        gaslighting_keywords = self._check_keywords(dialogue, self.rules["gaslighting_keywords"])
        
        # 判断风险等级和类型
        all_keywords = (
            pua_keywords +
            scam_keywords +
            emotional_blackmail_keywords +
            gaslighting_keywords
        )
        
        if not all_keywords:
            return SafetyCheckResult(
                is_safe=True,
                risk_level=RiskLevel.SAFE,
                risk_type=RiskType.NONE,
                reason="未检测到风险关键词",
                keywords=[],
                suggestion=None
            )
        
        # 确定主要风险类型
        risk_type, risk_keywords, suggestion = self._determine_risk_type(
            pua_keywords, scam_keywords, emotional_blackmail_keywords, gaslighting_keywords
        )
        
        # 确定风险等级
        risk_level = self._determine_risk_level(len(risk_keywords))
        
        result = SafetyCheckResult(
            is_safe=False,
            risk_level=risk_level,
            risk_type=risk_type,
            reason=f"检测到 {len(risk_keywords)} 个风险关键词",
            keywords=risk_keywords,
            suggestion=suggestion
        )
        
        logger.warning(f"⚠️ Safety risk detected: {risk_type} - Level: {risk_level}")
        return result
    
    def _check_keywords(self, text: str, keywords: List[str]) -> List[str]:
        """检查文本中是否包含关键词"""
        found = []
        for keyword in keywords:
            if keyword in text:
                found.append(keyword)
        return found
    
    def _determine_risk_type(
        self,
        pua_keywords: List[str],
        scam_keywords: List[str],
        emotional_blackmail_keywords: List[str],
        gaslighting_keywords: List[str]
    ) -> tuple[RiskType, List[str], str]:
        """确定主要风险类型"""
        # 按严重程度排序
        if scam_keywords:
            return (
                RiskType.SCAM,
                scam_keywords,
                self.rules["safe_suggestions"]["scam"]
            )
        elif pua_keywords:
            return (
                RiskType.PUA,
                pua_keywords,
                self.rules["safe_suggestions"]["pua"]
            )
        elif gaslighting_keywords:
            return (
                RiskType.GASLIGHTING,
                gaslighting_keywords,
                self.rules["safe_suggestions"]["gaslighting"]
            )
        elif emotional_blackmail_keywords:
            return (
                RiskType.EMOTIONAL_BLACKMAIL,
                emotional_blackmail_keywords,
                self.rules["safe_suggestions"]["emotional_blackmail"]
            )
        else:
            return (RiskType.NONE, [], "")
    
    def _determine_risk_level(self, keyword_count: int) -> RiskLevel:
        """确定风险等级"""
        high_threshold = self.rules["risk_patterns"]["high_risk"]["threshold"]
        medium_threshold = self.rules["risk_patterns"]["medium_risk"]["threshold"]
        
        if keyword_count >= high_threshold:
            return RiskLevel.HIGH
        elif keyword_count >= medium_threshold:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW


__all__ = ["SafetyService"]
