"""Sanitization and lightweight dedup helpers."""

from __future__ import annotations

import hashlib
import re
from typing import Iterable, Set


RE_URL = re.compile(r"https?://[^\s]+")
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
RE_PHONE = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
RE_WECHAT = re.compile(r"(微信|vx|v信|wechat)[:：]?\s*[A-Za-z0-9_-]{5,}")
RE_QQ = re.compile(r"(QQ|qq)[:：]?\s*\d{5,12}")
RE_ID18 = re.compile(r"\b\d{17}[\dXx]\b")
RE_ORDER = re.compile(r"(订单号|单号|流水号)[:：]?\s*[A-Za-z0-9-]{6,}")
RE_MULTI_SPACE = re.compile(r"\s+")


def sanitize_text(text: str) -> str:
    s = text or ""
    s = RE_URL.sub(" ", s)
    s = RE_EMAIL.sub(" ", s)
    s = RE_PHONE.sub(" ", s)
    s = RE_WECHAT.sub(" ", s)
    s = RE_QQ.sub(" ", s)
    s = RE_ID18.sub(" ", s)
    s = RE_ORDER.sub(" ", s)
    s = s.replace("\u200b", " ")
    s = RE_MULTI_SPACE.sub(" ", s).strip()
    return s


def normalize_text(text: str) -> str:
    s = (text or "").lower().strip()
    s = re.sub(r"[，。！？；：、“”‘’（）\(\)\[\]{}<>《》—\-~`!@#$%^&*+=|\\/:;\"',.?]", " ", s)
    s = RE_MULTI_SPACE.sub(" ", s).strip()
    return s


def char_ngrams(text: str, n: int = 3) -> Set[str]:
    t = normalize_text(text)
    if len(t) < n:
        return {t} if t else set()
    return {t[i : i + n] for i in range(len(t) - n + 1)}


def jaccard_similarity(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union


def near_duplicate(a_text: str, b_text: str, threshold: float = 0.9) -> bool:
    return jaccard_similarity(char_ngrams(a_text), char_ngrams(b_text)) >= threshold


def stable_hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]

