"""MBTI style profiles and label enums used by data scripts."""

from typing import Dict, List


MBTI_STYLES: Dict[str, str] = {
    "INTJ": (
        "理性、简洁、目标导向。强调事实、边界和执行计划。"
        "避免过度情绪化和空泛共情。"
    ),
    "ENFP": (
        "温暖、有感染力、关系导向。强调理解与可能性，"
        "语气自然有温度，但不过度讨好。"
    ),
    "ISTJ": (
        "稳重、务实、重责任。强调流程、规则和可交付时间点，"
        "表达克制清晰。"
    ),
    "ESFP": (
        "亲和、自然、当下感强。表达口语化，缓和气氛，"
        "但保留必要边界，不回避核心诉求。"
    ),
}


SCENARIOS: List[str] = ["workplace", "intimate", "family", "social"]
INTENTS: List[str] = ["refuse", "boundary", "request", "clarify", "comfort"]


def normalize_scenario(value: str) -> str:
    value = (value or "").strip().lower()
    return value if value in SCENARIOS else "social"


def normalize_intent(value: str) -> str:
    value = (value or "").strip().lower()
    return value if value in INTENTS else "clarify"

