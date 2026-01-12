"""
统一日志配置 (Loguru)

为整个应用提供统一的日志记录功能。
"""

import sys
from loguru import logger
from pathlib import Path

# 日志配置
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 移除默认的 handler
logger.remove()

# 添加控制台输出 (开发环境)
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    colorize=True,
)

# 添加文件输出 (所有日志)
logger.add(
    LOG_DIR / "resona_{time:YYYY-MM-DD}.log",
    rotation="00:00",  # 每天午夜轮转
    retention="30 days",  # 保留30天
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    encoding="utf-8",
)

# 添加错误日志文件
logger.add(
    LOG_DIR / "error_{time:YYYY-MM-DD}.log",
    rotation="00:00",
    retention="90 days",  # 错误日志保留90天
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    encoding="utf-8",
)


def get_logger(name: str):
    """
    获取一个带有指定名称的logger实例
    
    Args:
        name: logger 名称（通常使用 __name__）
        
    Returns:
        logger 实例
    """
    return logger.bind(name=name)


__all__ = ["logger", "get_logger"]
