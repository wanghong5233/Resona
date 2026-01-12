"""
枚举类型定义

定义应用中使用的所有枚举类型（MBTI、场景、意图等）。
"""

from enum import Enum


class MBTIType(str, Enum):
    """MBTI 人格类型（16 种）"""
    
    # 分析师 (Analysts)
    INTJ = "INTJ"  # 建筑师
    INTP = "INTP"  # 逻辑学家
    ENTJ = "ENTJ"  # 指挥官
    ENTP = "ENTP"  # 辩论家
    
    # 外交官 (Diplomats)
    INFJ = "INFJ"  # 提倡者
    INFP = "INFP"  # 调停者
    ENFJ = "ENFJ"  # 主人公
    ENFP = "ENFP"  # 竞选者
    
    # 守护者 (Sentinels)
    ISTJ = "ISTJ"  # 物流师
    ISFJ = "ISFJ"  # 守卫者
    ESTJ = "ESTJ"  # 总经理
    ESFJ = "ESFJ"  # 执政官
    
    # 探险家 (Explorers)
    ISTP = "ISTP"  # 鉴赏家
    ISFP = "ISFP"  # 探险家
    ESTP = "ESTP"  # 企业家
    ESFP = "ESFP"  # 表演者


class ScenarioType(str, Enum):
    """场景类型"""
    
    WORKPLACE = "workplace"          # 职场
    INTIMATE = "intimate"            # 亲密关系
    FAMILY = "family"                # 家庭
    FRIENDSHIP = "friendship"        # 友情
    SOCIAL = "social"                # 一般社交


class IntentType(str, Enum):
    """意图类型（用户想要表达的意图）"""
    
    REFUSE = "refuse"                # 拒绝（拒绝加班、拒绝要求）
    APOLOGIZE = "apologize"          # 道歉
    REQUEST = "request"              # 提要求
    BOUNDARY = "boundary"            # 设定边界
    COMFORT = "comfort"              # 安抚情绪
    EXPLAIN = "explain"              # 解释说明
    GRATITUDE = "gratitude"          # 表达感谢
    CLARIFY = "clarify"              # 澄清误会


class ReplyStyle(str, Enum):
    """回复风格标签"""
    
    MATURE = "mature"                # 成熟
    GENTLE = "gentle"                # 温和
    FIRM = "firm"                    # 坚定
    HUMOROUS = "humorous"            # 幽默
    RATIONAL = "rational"            # 理性
    EMPATHETIC = "empathetic"        # 共情


class RiskLevel(str, Enum):
    """风险等级"""
    
    SAFE = "safe"                    # 🟢 安全
    LOW = "low"                      # 🟡 低风险
    MEDIUM = "medium"                # 🟡 中风险
    HIGH = "high"                    # 🔴 高风险


class RiskType(str, Enum):
    """风险类型"""
    
    PUA = "pua"                      # PUA（打压→关怀→控制）
    SCAM = "scam"                    # 诈骗（冒充公检法、杀猪盘等）
    EMOTIONAL_BLACKMAIL = "emotional_blackmail"  # 情绪勒索
    GASLIGHTING = "gaslighting"      # 煤气灯效应
    NONE = "none"                    # 无风险


class LLMBackend(str, Enum):
    """LLM 后端类型"""
    
    MOCK = "mock"                    # Mock（用于测试）
    GPT4 = "gpt4"                    # OpenAI GPT-4
    DASHSCOPE = "dashscope"          # 阿里云通义千问
    QWEN = "qwen"                    # Ollama Qwen（本地部署）
    FINETUNED = "finetuned"          # 自训练模型（vLLM）


__all__ = [
    "MBTIType",
    "ScenarioType",
    "IntentType",
    "ReplyStyle",
    "RiskLevel",
    "RiskType",
    "LLMBackend",
]
