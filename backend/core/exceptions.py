"""
自定义异常类

定义应用中使用的所有自定义异常。
"""


class ResonaException(Exception):
    """Resona 基础异常类"""
    
    def __init__(self, message: str, code: str = "RESONA_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)


class LLMServiceError(ResonaException):
    """LLM 服务调用异常"""
    
    def __init__(self, message: str, provider: str = "unknown"):
        self.provider = provider
        super().__init__(message, code="LLM_SERVICE_ERROR")


class InvalidMBTIError(ResonaException):
    """无效的 MBTI 类型"""
    
    def __init__(self, mbti: str):
        message = f"无效的 MBTI 类型: {mbti}。有效类型: INTJ, INFJ, ISTJ, ISFJ, INTP, INFP, ISTP, ISFP, ENTJ, ENFJ, ESTJ, ESFJ, ENTP, ENFP, ESTP, ESFP"
        super().__init__(message, code="INVALID_MBTI")


class InvalidScenarioError(ResonaException):
    """无效的场景类型"""
    
    def __init__(self, scenario: str):
        message = f"无效的场景类型: {scenario}"
        super().__init__(message, code="INVALID_SCENARIO")


class InvalidIntentError(ResonaException):
    """无效的意图类型"""
    
    def __init__(self, intent: str):
        message = f"无效的意图类型: {intent}"
        super().__init__(message, code="INVALID_INTENT")


class CacheError(ResonaException):
    """缓存操作异常"""
    
    def __init__(self, message: str):
        super().__init__(message, code="CACHE_ERROR")


class ConfigError(ResonaException):
    """配置读取异常"""
    
    def __init__(self, message: str):
        super().__init__(message, code="CONFIG_ERROR")


class PromptTemplateError(ResonaException):
    """Prompt 模板错误"""
    
    def __init__(self, message: str, template_name: str = "unknown"):
        self.template_name = template_name
        super().__init__(message, code="PROMPT_TEMPLATE_ERROR")


__all__ = [
    "ResonaException",
    "LLMServiceError",
    "InvalidMBTIError",
    "InvalidScenarioError",
    "InvalidIntentError",
    "CacheError",
    "ConfigError",
    "PromptTemplateError",
]
