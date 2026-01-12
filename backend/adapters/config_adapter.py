"""
Config Adapter - 配置文件读取适配器

支持读取 YAML 和 JSON 格式的配置文件。
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any
from core.logger import logger
from core.exceptions import ConfigError
from config import settings


class ConfigAdapter:
    """配置文件适配器"""
    
    @staticmethod
    def load_yaml(file_path: Path) -> Dict[str, Any]:
        """
        加载 YAML 配置文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                logger.debug(f"📄 Loaded YAML config: {file_path}")
                return config or {}
        except FileNotFoundError:
            logger.error(f"❌ Config file not found: {file_path}")
            raise ConfigError(f"配置文件不存在: {file_path}")
        except yaml.YAMLError as e:
            logger.error(f"❌ Invalid YAML format: {e}")
            raise ConfigError(f"YAML 格式错误: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to load YAML: {e}")
            raise ConfigError(f"加载配置文件失败: {e}")
    
    @staticmethod
    def load_json(file_path: Path) -> Dict[str, Any]:
        """
        加载 JSON 配置文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            配置字典
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.debug(f"📄 Loaded JSON config: {file_path}")
                return config
        except FileNotFoundError:
            logger.error(f"❌ Config file not found: {file_path}")
            raise ConfigError(f"配置文件不存在: {file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON format: {e}")
            raise ConfigError(f"JSON 格式错误: {e}")
        except Exception as e:
            logger.error(f"❌ Failed to load JSON: {e}")
            raise ConfigError(f"加载配置文件失败: {e}")
    
    @staticmethod
    def load_prompt_template(template_name: str) -> Dict[str, Any]:
        """
        加载 Prompt 模板
        
        Args:
            template_name: 模板名称（不含扩展名）
            
        Returns:
            模板配置字典
        """
        file_path = settings.PROMPTS_DIR / f"{template_name}.yaml"
        return ConfigAdapter.load_yaml(file_path)
    
    @staticmethod
    def load_safety_rules() -> Dict[str, Any]:
        """
        加载安全规则配置
        
        Returns:
            安全规则字典
        """
        file_path = settings.RULES_DIR / "safety_keywords.json"
        return ConfigAdapter.load_json(file_path)


__all__ = ["ConfigAdapter"]
