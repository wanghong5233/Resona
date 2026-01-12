"""
智能分析服务

负责识别对话场景、意图。

说明：
- MVP 阶段先用「关键词规则」做一个可用的自动识别
- 后续可升级为 LLM 语义分类（并输出证据句/置信度）
"""

from typing import Tuple

from core.enums import IntentType, ScenarioType
from core.logger import logger


class AnalysisService:
    """智能分析服务（关键词规则 + LLM 语义分析）"""
    
    # 场景关键词规则
    SCENARIO_KEYWORDS = {
        ScenarioType.WORKPLACE.value: [
            "老板", "领导", "上司", "经理", "总监", "主管",
            "加班", "工作", "项目", "会议", "报告", "任务",
            "同事", "客户", "业绩", "KPI", "考核"
        ],
        ScenarioType.INTIMATE.value: [
            "女朋友", "男朋友", "宝贝", "亲爱的", "老公", "老婆",
            "爱你", "想你", "生气", "吵架", "约会", "恋爱",
            "分手", "复合", "表白", "喜欢"
        ],
        ScenarioType.FAMILY.value: [
            "妈妈", "爸爸", "父母", "儿子", "女儿", "孩子",
            "家里", "回家", "父亲", "母亲", "爷爷", "奶奶",
            "哥哥", "姐姐", "弟弟", "妹妹"
        ],
        ScenarioType.FRIENDSHIP.value: [
            "朋友", "兄弟", "闺蜜", "同学", "室友",
            "聚会", "玩", "一起", "帮忙", "借钱"
        ],
        ScenarioType.SOCIAL.value: [
            "客气", "麻烦", "感谢", "不好意思", "打扰",
            "认识", "交流", "沟通"
        ]
    }
    
    # 意图关键词规则
    INTENT_KEYWORDS = {
        IntentType.REFUSE.value: [
            "不", "拒绝", "不方便", "不太好", "不行",
            "周末", "休息", "忙", "没空", "不想",
            "算了", "下次", "改天", "不能", "没法"
        ],
        IntentType.APOLOGIZE.value: [
            "对不起", "抱歉", "不好意思", "sorry",
            "错了", "我的错", "是我不对"
        ],
        IntentType.REQUEST.value: [
            "能不能", "可以吗", "麻烦你", "帮我", "请你", "请问",
            "?", "？"
        ],
        IntentType.BOUNDARY.value: [
            "请不要", "别再", "到此为止", "底线", "界限", "边界",
            "请尊重", "不要这样"
        ],
        IntentType.COMFORT.value: [
            "别难过", "没事的", "别伤心", "理解你", "抱抱",
            "别想太多", "我在", "会好的"
        ],
        IntentType.EXPLAIN.value: [
            "因为", "原因", "解释", "说明", "其实", "我的意思是"
        ],
        IntentType.GRATITUDE.value: [
            "谢谢", "感谢", "多谢", "thank", "辛苦了", "麻烦了"
        ],
        IntentType.CLARIFY.value: [
            "澄清", "误会", "不是", "我没有", "并不是", "你理解错了"
        ],
    }
    
    def analyze_dialogue(
        self, 
        dialogue_text: str
    ) -> Tuple[str, str, float]:
        """
        分析对话场景和意图
        
        Args:
            dialogue_text: 对话文本（多轮）
            
        Returns:
            (scenario, intent, confidence)
        """
        logger.info("🔍 Analysis: Analyzing dialogue...")
        
        # 1. 场景识别
        scenario, scenario_confidence = self._detect_scenario(dialogue_text)
        
        # 2. 意图识别
        intent, intent_confidence = self._detect_intent(dialogue_text)
        
        # 综合置信度
        confidence = (scenario_confidence + intent_confidence) / 2
        
        logger.info(
            f"✅ Analysis: scenario={scenario}, intent={intent}, "
            f"confidence={confidence:.2f}"
        )
        
        return scenario, intent, confidence
    
    def _detect_scenario(self, text: str) -> Tuple[str, float]:
        """
        检测场景
        
        Returns:
            (scenario, confidence)
        """
        max_score = 0
        detected_scenario = ScenarioType.SOCIAL.value  # 默认社交场景
        
        for scenario, keywords in self.SCENARIO_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > max_score:
                max_score = score
                detected_scenario = scenario
        
        # 计算置信度（命中关键词数量 / 5，最大 1.0）
        confidence = min(max_score / 5.0, 1.0)
        
        # 如果置信度太低，使用默认场景
        if confidence < 0.2:
            detected_scenario = ScenarioType.SOCIAL.value
            confidence = 0.5
        
        return detected_scenario, confidence
    
    def _detect_intent(self, text: str) -> Tuple[str, float]:
        """
        检测意图
        
        Returns:
            (intent, confidence)
        """
        max_score = 0
        detected_intent = IntentType.EXPLAIN.value  # 默认：解释
        
        for intent, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > max_score:
                max_score = score
                detected_intent = intent
        
        # 计算置信度
        confidence = min(max_score / 3.0, 1.0)
        
        # 如果置信度太低，使用默认意图
        if confidence < 0.3:
            detected_intent = IntentType.EXPLAIN.value
            confidence = 0.5
        
        return detected_intent, confidence
    
    # 风险检测不在这里做：ReplyService 已经统一做 safety check 并返回 RiskWarning
