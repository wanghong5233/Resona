"""
Prompt Service - Prompt 组装服务

负责动态组装 Prompt 模板。
"""

from jinja2 import Template
from core.logger import logger
from core.enums import MBTIType, ScenarioType, IntentType
from core.exceptions import PromptTemplateError
from adapters.config_adapter import ConfigAdapter


class PromptService:
    """Prompt 组装服务"""
    
    def __init__(self):
        self.config = ConfigAdapter()
        self.base_template = self.config.load_prompt_template("base_template")
        self.mbti_styles = self.config.load_prompt_template("mbti_styles")
        self.scenarios = self.config.load_prompt_template("scenarios")
    
    def build_prompt(
        self,
        dialogue: str,
        mbti: MBTIType,
        scenario: ScenarioType,
        intent: IntentType,
        context: str = None
    ) -> str:
        """
        构建 Prompt
        
        Args:
            dialogue: 对话内容
            mbti: MBTI 类型
            scenario: 场景类型
            intent: 意图类型
            context: 额外上下文
            
        Returns:
            完整的 Prompt
        """
        logger.info(f"📝 PromptService: Building prompt")
        logger.debug(f"📊 Parameters: MBTI={mbti}, Scenario={scenario}, Intent={intent}")
        
        try:
            # 获取 MBTI 风格指南
            mbti_style = self.mbti_styles.get(mbti.value, self.mbti_styles.get("default"))
            style_guide = mbti_style.get("style_guide", "")
            logger.debug(f"✅ MBTI style loaded: {mbti.value}")
            
            # 获取场景指南
            scenario_config = self.scenarios.get(scenario.value, {})
            scenario_guidelines = scenario_config.get("guidelines", "")
            logger.debug(f"✅ Scenario loaded: {scenario.value}")
            
            # 组装 Prompt
            template_str = self.base_template["base_template"]
            template = Template(template_str)
            
            prompt = template.render(
                dialogue=dialogue,
                mbti=mbti.value,
                scenario=scenario.value,
                intent=intent.value,
                context=context,
                style_guide=style_guide,
                scenario_guidelines=scenario_guidelines
            )
            
            logger.info(f"✅ Prompt built successfully, length={len(prompt)} chars")
            return prompt
            
        except Exception as e:
            logger.exception(f"❌ Failed to build prompt: {e}")
            raise PromptTemplateError(f"Prompt 构建失败: {e}")


__all__ = ["PromptService"]
