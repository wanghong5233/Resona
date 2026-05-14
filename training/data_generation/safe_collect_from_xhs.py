"""
Scenario-specific Xiaohongshu collector for dialogue-pair training data.

Design principles for this version:
- Goal-first: prioritize collecting (parent_comment -> high-liked reply) pairs.
- Click-first: enter note detail from search results by clicking cards.
- Stream-first: write usable note samples continuously, no giant URL pre-collection stage.
- Safety-first: explicit rate-limit detection, cooldown, and conservative pacing.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import traceback
import urllib.parse
import zlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TextIO

import atexit
import subprocess

from playwright.sync_api import sync_playwright


_RUN_LOG_FP: Optional[TextIO] = None
_EXIT_CODE_RATE_LIMIT = 42
_EXIT_CODE_SELF_RESTART = 43

# 模块级 browser/context 引用，atexit 时强制关闭，防止僵尸 Chrome 进程
_pw_browser: Any = None
_pw_context: Any = None


def _count_running_collectors() -> int:
    """Count running safe_collect_from_xhs.py processes (Windows only)."""
    try:
        import os

        if os.name != "nt":
            return 0
        result = subprocess.run(
            [
                "wmic",
                "process",
                "where",
                "name='python.exe' and CommandLine like '%safe_collect_from_xhs.py%'",
                "get",
                "ProcessId",
                "/format:list",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            errors="ignore",
            check=False,
        )
        cnt = 0
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("ProcessId="):
                pid_str = line.split("=", 1)[1].strip()
                if pid_str.isdigit():
                    cnt += 1
        return cnt
    except Exception:
        return 0


def _kill_playwright_orphans() -> None:
    """强制结束所有 ms-playwright 目录下的孤儿 Chrome 进程。"""
    try:
        result = subprocess.run(
            ["wmic", "process", "where",
             "name='chrome.exe' and ExecutablePath like '%ms-playwright%'",
             "get", "ProcessId", "/format:list"],
            capture_output=True, text=True, timeout=15, errors="ignore",
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("ProcessId="):
                pid_str = line.split("=", 1)[1].strip()
                if pid_str.isdigit():
                    subprocess.run(
                        ["taskkill", "/PID", pid_str, "/F"],
                        capture_output=True, check=False,
                    )
    except Exception:
        pass


def _atexit_browser_cleanup() -> None:
    """atexit 回调：确保 browser/context 被关闭，避免孤儿 Chrome 进程。"""
    global _pw_context, _pw_browser
    for obj, name in [(_pw_context, "context"), (_pw_browser, "browser")]:
        if obj is not None:
            try:
                obj.close()
            except Exception:
                pass
    _pw_context = None
    _pw_browser = None
    # 兜底：仅在没有其他 collector 在跑时才杀 ms-playwright Chrome，避免 A/B 并行互相误杀。
    if _count_running_collectors() <= 1:
        _kill_playwright_orphans()


atexit.register(_atexit_browser_cleanup)


def _looks_like_driver_disconnected(exc: BaseException) -> bool:
    s = str(exc) or ""
    return any(
        m in s
        for m in [
            "Connection closed while reading from the driver",
            "Connection closed",
            "Target closed",
            "Target page, context or browser has been closed",
            "Browser has been closed",
        ]
    )


class _TeeStream:
    """Duplicate writes to multiple streams (stdout/stderr + run log file)."""

    def __init__(self, streams: List[TextIO]) -> None:
        self._streams = [s for s in streams if s is not None]
        self.encoding = "utf-8"

    def write(self, data: str) -> int:
        for s in self._streams:
            try:
                s.write(data)
            except Exception:
                pass
        return len(data)

    def flush(self) -> None:
        for s in self._streams:
            try:
                s.flush()
            except Exception:
                pass

    def isatty(self) -> bool:
        for s in self._streams:
            try:
                if hasattr(s, "isatty") and s.isatty():
                    return True
            except Exception:
                continue
        return False


def setup_run_logging(log_path: Path) -> Path:
    """
    Redirect both stdout/stderr to terminal + file, eliminating log blind spots.
    """
    global _RUN_LOG_FP
    ensure_parent(log_path)
    _RUN_LOG_FP = log_path.open("a", encoding="utf-8", buffering=1)
    sys.stdout = _TeeStream([sys.__stdout__, _RUN_LOG_FP])  # type: ignore[assignment]
    sys.stderr = _TeeStream([sys.__stderr__, _RUN_LOG_FP])  # type: ignore[assignment]
    return log_path


def normalize_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if not u.startswith("http"):
        u = "https://" + u
    if "xiaohongshu.com" in u and "www.xiaohongshu.com" not in u:
        u = u.replace("xiaohongshu.com", "www.xiaohongshu.com")
    return u


def read_lines(path: Path) -> List[str]:
    if not path.exists():
        return []
    return [x.strip() for x in path.read_text(encoding="utf-8").splitlines() if x.strip() and not x.strip().startswith("#")]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def extract_note_id(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    for prefix in ("/search_result/", "/explore/", "/discovery/item/"):
        if prefix in u:
            rest = u.split(prefix, 1)[-1].split("?")[0].split("/")[0]
            if rest and len(rest) >= 10:
                return rest
    m = re.search(r"(?:note_id|noteId|id)=([0-9a-zA-Z]{10,})", u)
    if m:
        return m.group(1)
    return ""


def build_search_url(keyword: str) -> str:
    kw = urllib.parse.quote_plus(keyword)
    return f"https://www.xiaohongshu.com/search_result?keyword={kw}"


def _truncate(s: str, n: int) -> str:
    t = (s or "").strip()
    if len(t) <= n:
        return t
    return t[:n] + "...(truncated)"


def _safe_name(s: str) -> str:
    t = re.sub(r"[^a-zA-Z0-9._-]+", "_", (s or "").strip())
    return t[:80] or "x"


def sleep_with_jitter(base_sec: float, jitter_sec: float) -> None:
    base = max(0.0, float(base_sec))
    jitter = max(0.0, float(jitter_sec))
    time.sleep(base + random.uniform(0.0, jitter))


def _parse_like_count(text: str) -> int:
    t = (text or "").strip().lower()
    if not t:
        return 0
    t = (
        t.replace("点赞", "")
        .replace("赞", "")
        .replace("喜欢", "")
        .replace(",", "")
        .replace(" ", "")
        .replace("+", "")
    )
    m = re.search(r"(\d+(?:\.\d+)?)\s*万", t)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*w", t)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*k", t)
    if m:
        return int(float(m.group(1)) * 1000)
    m = re.search(r"\d+(?:\.\d+)?", t)
    if m:
        try:
            return int(float(m.group(0)))
        except Exception:
            return 0
    return 0


def _extract_number_with_unit(text: str) -> int:
    t = (text or "").strip().lower().replace(",", "")
    if not t:
        return 0
    m = re.search(r"(\d+(?:\.\d+)?)\s*万", t)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*w", t)
    if m:
        return int(float(m.group(1)) * 10000)
    m = re.search(r"(\d+(?:\.\d+)?)\s*k", t)
    if m:
        return int(float(m.group(1)) * 1000)
    m = re.search(r"\d+(?:\.\d+)?", t)
    if not m:
        return 0
    try:
        return int(float(m.group(0)))
    except Exception:
        return 0


def _extract_metric_value(text: str, metric_label: str) -> Optional[int]:
    t = (text or "").strip()
    if not t:
        return None
    patterns = [
        rf"{re.escape(metric_label)}\s*[:：]?\s*(\d+(?:\.\d+)?\s*[万wWkK]?)",
        rf"(\d+(?:\.\d+)?\s*[万wWkK]?)\s*{re.escape(metric_label)}",
    ]
    for p in patterns:
        m = re.search(p, t, flags=re.IGNORECASE)
        if not m:
            continue
        val = _extract_number_with_unit(m.group(1))
        if val >= 0:
            return val
    return None


def extract_card_hints(anchor) -> tuple[int, int]:
    """
    从搜索卡片文本里提取 comment/like 提示值。
    修复点：
    1) 很多页面 a 标签自身文本为空，改为向上抓取卡片容器文本；
    2) 同时兼容 “评论 12 / 12评论 / 点赞 3.2万 / 3.2万赞” 等写法。
    未提取到返回 -1（unknown）。
    """
    payload: Dict[str, Any] = {}
    js = r"""
(el) => {
  const toInt = (s) => {
    if (!s) return -1;
    const t = String(s).replace(/[,，\s]/g, '').toLowerCase();
    const m = t.match(/(\d+(?:\.\d+)?)(万|w|k)?/i);
    if (!m) return -1;
    let v = parseFloat(m[1]);
    const unit = (m[2] || '').toLowerCase();
    if (unit === '万' || unit === 'w') v *= 10000;
    else if (unit === 'k') v *= 1000;
    return Number.isFinite(v) ? Math.floor(v) : -1;
  };

  const parseMetric = (text, labels) => {
    const src = String(text || '');
    if (!src) return -1;
    const compact = src.replace(/\s+/g, ' ');
    for (const lb of labels) {
      let m = compact.match(new RegExp(`${lb}\\s*[:：]?\\s*(\\d+(?:\\.\\d+)?\\s*[万wWkK]?)`, 'i'));
      if (m) {
        const n = toInt(m[1]);
        if (n >= 0) return n;
      }
      m = compact.match(new RegExp(`(\\d+(?:\\.\\d+)?\\s*[万wWkK]?)\\s*${lb}`, 'i'));
      if (m) {
        const n = toInt(m[1]);
        if (n >= 0) return n;
      }
    }
    return -1;
  };

  const texts = [];
  const pushText = (node) => {
    if (!node) return;
    const t = (node.innerText || node.textContent || '').trim();
    if (t) texts.push(t);
  };

  pushText(el);
  let p = el;
  for (let i = 0; i < 5; i++) {
    p = p && p.parentElement;
    if (!p) break;
    pushText(p);
  }
  try {
    const card = el.closest('section, article, li, [class*="note-item"], [class*="feed"], [class*="card"]');
    pushText(card);
  } catch (_) {}

  let best = '';
  for (const t of texts) {
    if (t.length > best.length) best = t;
  }

  return {
    card_text: best,
    comment_hint: parseMetric(best, ['评论', '条评论']),
    like_hint: parseMetric(best, ['点赞', '赞', '喜欢'])
  };
}
"""
    try:
        payload = anchor.evaluate(js) or {}
    except Exception:
        payload = {}

    card_text = str(payload.get("card_text") or "").strip()
    try:
        comment_hint = int(payload.get("comment_hint", -1))
    except Exception:
        comment_hint = -1
    try:
        like_hint = int(payload.get("like_hint", -1))
    except Exception:
        like_hint = -1

    # JS 未命中时走 Python 正则兜底
    if comment_hint < 0:
        py_comment = _extract_metric_value(card_text, "评论")
        comment_hint = py_comment if py_comment is not None else -1
    if like_hint < 0:
        py_like = _extract_metric_value(card_text, "赞")
        if py_like is None:
            py_like = _extract_metric_value(card_text, "点赞")
        if py_like is None:
            py_like = _extract_metric_value(card_text, "喜欢")
        like_hint = py_like if py_like is not None else -1

    return (comment_hint, like_hint)


def _is_valid_reply_text(s: str) -> bool:
    if not s or len(s.strip()) < 4:
        return False
    t = s.strip()
    if t.isdigit():
        return False
    if "作者" in t and ("回复" in t or re.search(r"20\d{2}", t)):
        return False
    if re.search(r"20\d{2}-\d{2}-\d{2}", t) and "回复" in t:
        return False
    if re.match(r"^.+\d+回复$", t) and len(t) < 40:
        return False
    return True


def _is_valid_dialogue_output(s: str, min_len: int = 10) -> bool:
    if not s or len(s.strip()) < min_len:
        return False
    t = s.strip()
    if re.match(r"^@\S+$", t):
        return False
    if re.match(r"^\[[\w]+R\]$", t):
        return False
    return len(t) >= min_len


def looks_like_ad(text: str) -> bool:
    t = (text or "").lower()
    markers = [
        "vx",
        "v信",
        "微信",
        "wechat",
        "加我",
        "私信",
        "链接",
        "淘宝",
        "拼多多",
        "小店",
        "课程",
        "训练营",
        "带货",
        "推广",
        "返利",
        "领取",
        "扫码",
        "群",
        "号",
    ]
    return any(m in t for m in markers)


def detect_rate_limit_marker(page) -> str:
    try:
        cur = (page.url or "").lower()
    except Exception:
        cur = ""
    for m in ("website-login/error", "security", "sec_verify", "captcha"):
        if m in cur:
            return f"url:{m}"

    try:
        body = (page.text_content("body") or "").strip().lower()
    except Exception:
        body = ""
    if not body:
        return ""
    for m in ("安全限制", "访问频繁", "请稍后再试", "异常访问", "300013", "访问受限"):
        if m in body:
            return f"body:{m}"
    return ""


def is_note_unavailable(page) -> bool:
    try:
        cur = (page.url or "").lower()
        if "/404" in cur:
            return True
        body = (page.text_content("body") or "").strip()
        if not body:
            return False
        markers = [
            "当前笔记暂时无法浏览",
            "笔记暂时无法浏览",
            "内容不存在",
            "页面不存在",
            "内容已被删除",
            "请打开小红书app扫码查看",
            "扫码查看",
        ]
        return any(m in body for m in markers)
    except Exception:
        return False


def _scroll_comment_container(page) -> None:
    js = r"""
() => {
  const sels = [
    '.interaction-container',
    '[class*="interaction-container"]',
    '.comment-list',
    '[class*="comment-list"]',
    '.comments-container',
    '[class*="comments-container"]'
  ];
  let scrolled = false;
  for (const s of sels) {
    const el = document.querySelector(s);
    if (!el) continue;
    try {
      const before = el.scrollTop;
      el.scrollTop = el.scrollHeight;
      if (el.scrollTop !== before) scrolled = true;
    } catch (_) {}
  }
  if (!scrolled) window.scrollBy(0, 1200);
}
"""
    try:
        page.evaluate(js)
    except Exception:
        page.mouse.wheel(0, 1200)


def _click_text_if_present(page, label: str, click_timeout_ms: int = 380) -> bool:
    """
    只在文本节点存在时点击，避免 get_by_text 在元素不存在时长等待。
    """
    try:
        loc = page.get_by_text(label, exact=False)
        if loc.count() <= 0:
            return False
        btn = loc.first
        try:
            if hasattr(btn, "is_visible") and not btn.is_visible(timeout=120):
                return False
        except Exception:
            pass
        btn.click(timeout=click_timeout_ms)
        return True
    except Exception:
        return False


def detect_no_comment_marker(page) -> str:
    markers = [
        "暂无评论",
        "还没有评论",
        "还没评论",
        "评论已关闭",
        "评论区已关闭",
        "作者已关闭评论",
        "无法查看评论",
    ]
    try:
        body = (page.text_content("body") or "").strip()
    except Exception:
        body = ""
    if not body:
        return ""
    for m in markers:
        if m in body:
            return m
    return ""


def open_comments_panel(page, rounds: int = 3) -> None:
    labels = ["评论", "全部评论", "查看全部评论", "最新评论", "最热", "热门", "展开"]
    for _ in range(max(1, rounds)):
        clicked_any = False
        for label in labels:
            if _click_text_if_present(page, label, click_timeout_ms=380):
                clicked_any = True
                page.wait_for_timeout(180)
        _scroll_comment_container(page)
        page.wait_for_timeout(300 if clicked_any else 220)


def try_prefer_hot_comments(page) -> str:
    candidates = ["最热", "热门", "按热度", "热度", "综合"]
    for label in candidates:
        if _click_text_if_present(page, label, click_timeout_ms=500):
            page.wait_for_timeout(650)
            return label
    return ""


def expand_comments_for_capture(
    page,
    rounds: int = 8,
    sleep_ms: int = 700,
    note_hint: str = "",
    verbose: bool = False,
    max_seconds: float = 18.0,
) -> None:
    """展开评论区，遇到连续空轮会提前停止，避免单帖长时间空耗。"""
    labels = ["查看更多评论", "展开更多评论", "加载更多", "查看全部", "更多评论", "展开", "查看全部回复"]
    click_timeout_ms = 420
    idle_rounds = 0
    total_clicks = 0
    started = time.monotonic()
    for r in range(max(1, rounds)):
        if max_seconds > 0 and (time.monotonic() - started) >= max_seconds:
            if verbose:
                print(f"    [expand] note={note_hint} 提前停止：达到展开预算 {max_seconds:.1f}s", flush=True)
            break
        round_clicks = 0
        for label in labels:
            if _click_text_if_present(page, label, click_timeout_ms=click_timeout_ms):
                round_clicks += 1
                page.wait_for_timeout(420)
        total_clicks += round_clicks
        _scroll_comment_container(page)
        page.wait_for_timeout(sleep_ms)
        if round_clicks == 0:
            idle_rounds += 1
        else:
            idle_rounds = 0
        if verbose and ((r + 1) % 2 == 0 or round_clicks > 0):
            print(
                f"    [expand] note={note_hint} round={r + 1}/{rounds} "
                f"round_clicks={round_clicks} total_clicks={total_clicks}",
                flush=True,
            )
        # 连续两轮没有任何可点“更多”，提前退出
        if idle_rounds >= 2:
            if verbose:
                print(f"    [expand] note={note_hint} 提前停止：连续 {idle_rounds} 轮无可展开项", flush=True)
            break


_EXTRACT_CONTENT_JS = r"""
(el) => {
  const skip = /like|count|date|time|reply|interact|icon|expand|more|author|点赞|回复|互动/i;
  const candidates = [];
  for (const sel of ['.note-text', 'span[class*="note-text"]', '[class*="content"]:not([class*="like"]):not([class*="count"])', '[class*="comment-text"]', '[class*="desc"]']) {
    try {
      el.querySelectorAll(sel).forEach(n => {
        if (skip.test(n.className || '')) return;
        const t = (n.innerText || n.textContent || '').trim();
        if (t.length >= 4 && !/^\d+$/.test(t) && !(/\d{4}-\d{2}-\d{2}/.test(t) && /回复/.test(t)))
          candidates.push(t);
      });
    } catch (_) {}
  }
  if (candidates.length) {
    candidates.sort((a, b) => b.length - a.length);
    return candidates[0].slice(0, 500);
  }
  const full = (el.innerText || el.textContent || '').trim();
  const bad = /\S+\s*作者\s*[\d\-]+\s*\S*\s*\d*回复?\s*$|^\d+$/;
  if (bad.test(full)) return '';
  const stripped = full.replace(/\s*\S*作者\s*[\d\-]+\s*\S*\s*\d*回复?\s*$/i, '').trim();
  const out = stripped.length > full.length * 0.3 ? stripped : full;
  return (out.length >= 4 && !/^\d+$/.test(out)) ? out.slice(0, 500) : '';
}
"""


def _get_comment_text(el, text_selectors: List[str]) -> str:
    try:
        out = el.evaluate(_EXTRACT_CONTENT_JS)
        if out and _is_valid_reply_text(out):
            return out
    except Exception:
        pass
    for ts in text_selectors:
        children = el.query_selector_all(ts) if hasattr(el, "query_selector_all") else []
        for child in children:
            cls = (child.get_attribute("class") or "").lower()
            if "like" in cls or "count" in cls or "date" in cls or "interact" in cls:
                continue
            txt = (child.text_content() or "").strip()
            if not txt or len(txt) < 4 or txt.isdigit():
                continue
            if "作者" in txt and "回复" in txt:
                continue
            if re.search(r"20\d{2}-\d{2}-\d{2}", txt) and "回复" in txt:
                continue
            return txt[:500]
    raw = (el.text_content() or "").strip()[:500]
    return raw if _is_valid_reply_text(raw) else ""


def _get_comment_likes(el, like_selectors: List[str]) -> tuple[int, str]:
    for ls in like_selectors:
        child = el.query_selector(ls) if hasattr(el, "query_selector") else None
        if not child:
            continue
        raw = (child.text_content() or "").strip()
        n = _parse_like_count(raw)
        if raw or n > 0:
            return n, raw
    return 0, ""


def collect_comment_reply_pairs(
    page,
    max_pairs: int,
    min_reply_likes: int,
    max_parents: int = 25,
    expand_wait_ms: int = 600,
    max_depth: int = 2,
    time_budget_sec: float = 8.0,
) -> Dict[str, Any]:
    """
    只采集真实的父评论 -> 子回复对，不再构造 sibling_fallback 伪对话。
    """
    text_selectors = [".content", ".comment-content", ".content-text", "p", "span.note-text"]
    like_selectors = [".like-count", ".count", "span[class*='like']", "div[class*='like']", "span[class*='interact']"]
    reply_container_selectors = [".reply-list", ".sub-comment", ".comment-reply", "[class*='reply']", "[class*='child']"]

    parents = []
    for s in ["div.comment-item", ".comment-item", ".comment-wrapper"]:
        try:
            parents = page.query_selector_all(s)
        except Exception:
            parents = []
        if parents:
            break

    pairs: List[Dict[str, Any]] = []
    seen_pair_keys: Set[str] = set()
    threshold = max(0, int(min_reply_likes))
    started = time.monotonic()

    def _out_of_budget() -> bool:
        return time_budget_sec > 0 and (time.monotonic() - started) >= time_budget_sec

    max_depth = max(1, int(max_depth))
    for parent_el in parents[:max_parents]:
        if _out_of_budget():
            break
        if len(pairs) >= max_pairs:
            break
        try:
            parent_text = _get_comment_text(parent_el, text_selectors)
            if not parent_text or not _is_valid_reply_text(parent_text):
                continue
            if len(parent_text) > 300:
                parent_text = parent_text[:300] + "…"
            try:
                for node in parent_el.query_selector_all("button, a, span[role='button'], [class*='expand'], [class*='more']"):
                    t = (node.text_content() or "").strip()
                    if any(x in t for x in ["展开", "回复", "查看"]):
                        node.click(timeout=380)
                        page.wait_for_timeout(expand_wait_ms)
                        break
            except Exception:
                pass

            replies: List[Any] = []
            for rc in reply_container_selectors:
                try:
                    replies = parent_el.query_selector_all(rc)
                except Exception:
                    replies = []
                if replies:
                    break
            if not replies:
                try:
                    nested = parent_el.query_selector_all("[class*='comment-item'], [class*='reply'], .comment")
                except Exception:
                    nested = []
                replies = [n for n in nested if n != parent_el][:15]

            for reply_el in replies:
                if _out_of_budget():
                    break
                if len(pairs) >= max_pairs:
                    break
                try:
                    reply_text = _get_comment_text(reply_el, text_selectors)
                    if not reply_text:
                        continue
                    if not _is_valid_reply_text(reply_text) or not _is_valid_dialogue_output(reply_text):
                        continue
                    if reply_text == parent_text or reply_text in parent_text:
                        continue
                    reply_likes, likes_raw = _get_comment_likes(reply_el, like_selectors)
                    if threshold > 0 and reply_likes < threshold:
                        continue
                    key = f"{parent_text[:80]}|{reply_text[:80]}"
                    if key in seen_pair_keys:
                        continue
                    seen_pair_keys.add(key)
                    pairs.append(
                        {
                            "input": parent_text.strip(),
                            "output": reply_text.strip(),
                            "output_likes": reply_likes,
                            "output_likes_raw": likes_raw,
                            "source": "dom_parent_reply",
                            "thread_depth": 1,
                        }
                    )
                    if max_depth >= 2:
                        # DOM 兜底仅做一层近似深挖：把回复下的子回复当作 reply->reply 的边
                        try:
                            nested_nodes = reply_el.query_selector_all(
                                ".sub-comment, .comment-reply, [class*='reply'], [class*='child']"
                            )
                        except Exception:
                            nested_nodes = []
                        for nested in nested_nodes[:12]:
                            if _out_of_budget():
                                break
                            if len(pairs) >= max_pairs:
                                break
                            try:
                                nested_text = _get_comment_text(nested, text_selectors)
                                if not nested_text:
                                    continue
                                if not _is_valid_reply_text(nested_text) or not _is_valid_dialogue_output(nested_text):
                                    continue
                                if nested_text == reply_text or nested_text in reply_text:
                                    continue
                                n_like, n_raw = _get_comment_likes(nested, like_selectors)
                                if threshold > 0 and n_like < threshold:
                                    continue
                                nested_key = f"{reply_text[:80]}|{nested_text[:80]}"
                                if nested_key in seen_pair_keys:
                                    continue
                                seen_pair_keys.add(nested_key)
                                pairs.append(
                                    {
                                        "input": reply_text.strip(),
                                        "output": nested_text.strip(),
                                        "output_likes": n_like,
                                        "output_likes_raw": n_raw,
                                        "source": "dom_nested_reply",
                                        "thread_depth": 2,
                                    }
                                )
                            except Exception:
                                continue
                except Exception:
                    continue
        except Exception:
            continue

    high_like_count = sum(1 for p in pairs if int(p.get("output_likes", 0) or 0) >= max(1, threshold))
    return {
        "pairs": pairs[:max_pairs],
        "stats": {
            "selection_mode": "reply_pairs" if pairs else "no_pairs",
            "like_signal_found": any(int(p.get("output_likes", 0) or 0) > 0 for p in pairs),
            "total_pairs": len(pairs[:max_pairs]),
            "high_like_pairs": high_like_count,
            "min_reply_likes": threshold,
            "max_thread_depth_seen": max([int(p.get("thread_depth", 1) or 1) for p in pairs] or [0]),
        },
    }


def _parse_comment_api_response(resp, max_depth: int = 3) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    max_depth = max(1, int(max_depth))
    try:
        u = (resp.url or "").lower()
        if "xiaohongshu" not in u or "comment" not in u:
            return pairs
        body = resp.json()
    except Exception:
        return pairs

    data = body.get("data") or body
    comments: List[Dict[str, Any]] = []
    for candidate in (
        data.get("comments"),
        data.get("comment_list"),
        data.get("list"),
        data.get("items"),
        body.get("comments"),
    ):
        if isinstance(candidate, list):
            comments = [x for x in candidate if isinstance(x, dict)]
            if comments:
                break
    if not comments and isinstance(data.get("comment"), list):
        comments = [x for x in data["comment"] if isinstance(x, dict)]
    if not comments and isinstance(data.get("data"), dict):
        nested = data.get("data") or {}
        for k in ("comments", "comment_list", "list", "items"):
            v = nested.get(k)
            if isinstance(v, list):
                comments = [x for x in v if isinstance(x, dict)]
                if comments:
                    break

    def _content_of(node: Dict[str, Any]) -> str:
        return (
            node.get("content")
            or node.get("text")
            or node.get("note_card", {}).get("content")
            or node.get("desc")
            or ""
        ).strip()

    def _children_of(node: Dict[str, Any]) -> List[Dict[str, Any]]:
        for k in (
            "sub_comments",
            "sub_comment_list",
            "subComments",
            "subCommentList",
            "replies",
            "children",
            "reply_comment",
            "replyComment",
        ):
            v = node.get(k)
            if isinstance(v, list):
                return [x for x in v if isinstance(x, dict)]
            if isinstance(v, dict):
                return [v]
        return []

    def _id_of(node: Dict[str, Any]) -> str:
        return str(node.get("id") or node.get("comment_id") or node.get("commentId") or "").strip()

    def _likes_of(node: Dict[str, Any]) -> int:
        return int(node.get("like_count") or node.get("likeCount") or node.get("liked_count") or node.get("likes") or 0)

    seen_keys: Set[tuple[str, str]] = set()

    def _push_pair(input_text: str, output_text: str, likes: int, source: str, depth: int, root_text: str) -> None:
        inp = (input_text or "").strip()
        out = (output_text or "").strip()
        if not inp or not out:
            return
        if not _is_valid_reply_text(inp) or not _is_valid_reply_text(out):
            return
        if not _is_valid_dialogue_output(out):
            return
        if out == inp or out in inp:
            return
        key = (inp[:120], out[:120])
        if key in seen_keys:
            return
        seen_keys.add(key)
        pairs.append(
            {
                "input": inp[:300],
                "output": out[:500],
                "output_likes": int(likes or 0),
                "output_likes_raw": str(int(likes or 0)) if int(likes or 0) > 0 else "",
                "source": source,
                "thread_depth": max(1, int(depth)),
                "thread_root": (root_text or inp)[:300],
            }
        )

    def _walk_edges(parent_text: str, children: List[Dict[str, Any]], root_text: str, depth: int) -> None:
        if not children or len(pairs) >= 320 or depth > max_depth:
            return
        for child in children:
            if len(pairs) >= 320:
                break
            reply_text = _content_of(child)
            next_parent = parent_text
            if reply_text and _is_valid_reply_text(reply_text):
                likes = _likes_of(child)
                _push_pair(parent_text, reply_text, likes, "api_reply_edge", depth, root_text)
                next_parent = reply_text[:300]
            child_subs = _children_of(child)
            if child_subs:
                _walk_edges(next_parent, child_subs, root_text, depth + 1)

    # 先建 ID->内容映射，给“扁平 reply 列表”做 parent 反查
    id_to_text: Dict[str, str] = {}
    for c in comments:
        cid = _id_of(c)
        ctext = _content_of(c)
        if cid and ctext:
            id_to_text[cid] = ctext[:300]

    # 处理扁平结构：当前 comment 带 target_comment/parent_comment_id
    for c in comments:
        if len(pairs) >= 320:
            break
        reply_text = _content_of(c)
        if not reply_text:
            continue
        target = c.get("target_comment") or c.get("targetComment") or c.get("reply_to_comment") or c.get("replyToComment") or {}
        parent_text = _content_of(target) if isinstance(target, dict) else ""
        if not parent_text:
            parent_id = str(
                c.get("target_comment_id")
                or c.get("targetCommentId")
                or c.get("parent_comment_id")
                or c.get("parentCommentId")
                or ""
            ).strip()
            parent_text = id_to_text.get(parent_id, "")
        if parent_text:
            _push_pair(parent_text, reply_text, _likes_of(c), "api_target_reply", 1, parent_text)

    for c in comments:
        if not c or not isinstance(c, dict):
            continue
        parent_content = _content_of(c)
        if not parent_content or not _is_valid_reply_text(parent_content):
            continue
        if len(parent_content) > 300:
            parent_content = parent_content[:300] + "…"
        _walk_edges(parent_content, _children_of(c), parent_content, depth=1)
        if len(pairs) >= 320:
            break
    return pairs


def _dedupe_pairs(pairs: List[Dict[str, Any]], max_pairs: int) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    for p in pairs:
        key = ((p.get("input") or "")[:100], (p.get("output") or "")[:100])
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= max_pairs:
            break
    return out


def build_unavailable_item(url: str, min_comment_likes: int, reason: str) -> Dict[str, Any]:
    return {
        "platform": "xiaohongshu",
        "url": url,
        "dialogue_pairs": [],
        "pair_stats": {
            "selection_mode": "unavailable",
            "unavailable_reason": reason,
            "total_pairs": 0,
            "high_like_pairs": 0,
            "min_reply_likes": max(0, int(min_comment_likes)),
        },
        "fetch_meta": {
            "input_url": url,
            "final_url": url,
            "http_status": 0,
            "page_title": "",
            "body_head": "",
        },
        "collected_at": datetime.utcnow().isoformat() + "Z",
    }


def collect_note_from_current_page(
    page,
    input_url: str,
    max_comments: int,
    sleep_sec: float,
    min_comment_likes: int,
    page_timeout_ms: int,
    api_pairs: List[Dict[str, Any]],
    max_parents_per_note: int = 30,
    expand_rounds_per_note: int = 8,
    max_reply_depth: int = 3,
    status: int = 0,
    note_soft_timeout_sec: float = 45.0,
    note_hard_timeout_sec: float = 120.0,
    dom_fallback_max_seconds: float = 8.0,
    enable_dom_fallback: bool = False,
) -> Dict[str, Any]:
    final_url = ""
    try:
        final_url = (page.url or "").strip()
    except Exception:
        final_url = ""
    started_ts = time.monotonic()
    soft_budget_sec = max(10.0, float(note_soft_timeout_sec))
    hard_budget_sec = max(soft_budget_sec + 8.0, float(note_hard_timeout_sec))

    def _elapsed_sec() -> float:
        return max(0.0, time.monotonic() - started_ts)

    def _remaining_hard_sec() -> float:
        return max(0.0, hard_budget_sec - _elapsed_sec())

    if "/404" in (final_url or "").lower():
        item = build_unavailable_item(input_url, min_comment_likes, "redirect_404")
        item["fetch_meta"]["http_status"] = status
        item["fetch_meta"]["final_url"] = final_url or input_url
        return item

    rate_limit_marker = detect_rate_limit_marker(page)
    if rate_limit_marker:
        item = build_unavailable_item(input_url, min_comment_likes, "rate_limited")
        item["fetch_meta"]["http_status"] = status
        item["fetch_meta"]["final_url"] = final_url or input_url
        item["fetch_meta"]["rate_limit_marker"] = rate_limit_marker
        try:
            item["fetch_meta"]["page_title"] = (page.title() or "").strip()
        except Exception:
            pass
        try:
            body = (page.text_content("body") or "").strip()
            item["fetch_meta"]["body_head"] = _truncate(body, 400)
        except Exception:
            pass
        return item

    if status >= 400:
        item = build_unavailable_item(input_url, min_comment_likes, f"http_{status}")
        item["fetch_meta"]["http_status"] = status
        item["fetch_meta"]["final_url"] = final_url or input_url
        try:
            item["fetch_meta"]["page_title"] = (page.title() or "").strip()
        except Exception:
            pass
        try:
            body = (page.text_content("body") or "").strip()
            item["fetch_meta"]["body_head"] = _truncate(body, 400)
        except Exception:
            pass
        return item

    page.wait_for_timeout(int(max(1400, sleep_sec * 1000)))
    try:
        page.wait_for_selector(
            "#detail-desc, .note-content, article, div.comment-item, .comment-item",
            timeout=min(9000, max(1800, int(page_timeout_ms * 0.25))),
        )
    except Exception:
        pass
    page.mouse.wheel(0, 1100)
    page.wait_for_timeout(950)

    rate_limit_marker = detect_rate_limit_marker(page)
    if rate_limit_marker:
        item = build_unavailable_item(input_url, min_comment_likes, "rate_limited")
        item["fetch_meta"]["http_status"] = status
        item["fetch_meta"]["final_url"] = final_url or input_url
        item["fetch_meta"]["rate_limit_marker"] = rate_limit_marker
        try:
            item["fetch_meta"]["page_title"] = (page.title() or "").strip()
        except Exception:
            pass
        return item

    if is_note_unavailable(page):
        item = build_unavailable_item(input_url, min_comment_likes, "page_marker")
        item["fetch_meta"]["http_status"] = status
        item["fetch_meta"]["final_url"] = final_url or input_url
        try:
            item["fetch_meta"]["page_title"] = (page.title() or "").strip()
        except Exception:
            pass
        try:
            body = (page.text_content("body") or "").strip()
            item["fetch_meta"]["body_head"] = _truncate(body, 400)
        except Exception:
            pass
        return item

    threshold = max(0, int(min_comment_likes))

    def _select_api_pairs(like_threshold: int) -> List[Dict[str, Any]]:
        out = [
            p
            for p in api_pairs
            if _is_valid_dialogue_output(p.get("output", "") or "")
            and (like_threshold <= 0 or int(p.get("output_likes", 0) or 0) >= like_threshold)
        ]
        out.sort(key=lambda x: int(x.get("output_likes", 0) or 0), reverse=True)
        return _dedupe_pairs(out, max_comments)

    def _build_pair_stats(mode: str, pairs: List[Dict[str, Any]], extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        stats = {
            "selection_mode": mode,
            "like_signal_found": any(int(p.get("output_likes", 0) or 0) > 0 for p in pairs),
            "total_pairs": len(pairs),
            "high_like_pairs": sum(1 for p in pairs if int(p.get("output_likes", 0) or 0) >= max(1, threshold)),
            "min_reply_likes": threshold,
        }
        if extra:
            stats.update(extra)
        return stats

    fast_api_selected = _select_api_pairs(threshold)
    api_fast_keep = min(max_comments, max(4, min(8, max_comments // 2 if max_comments > 1 else 1)))

    if len(fast_api_selected) >= api_fast_keep:
        dialogue_pairs = fast_api_selected
        pair_stats = _build_pair_stats("api_fast", dialogue_pairs)
    elif fast_api_selected and _elapsed_sec() >= soft_budget_sec:
        # 软预算到达且 API 已有可用结果：优先收敛，避免单帖拖慢全局。
        dialogue_pairs = fast_api_selected
        pair_stats = _build_pair_stats("api_soft_budget_cut", dialogue_pairs)
    elif _remaining_hard_sec() <= 1.5:
        # 硬预算将耗尽，不再进入重度 DOM 处理。
        relaxed_api = fast_api_selected or _select_api_pairs(0)
        if relaxed_api:
            dialogue_pairs = relaxed_api
            pair_stats = _build_pair_stats("api_hard_budget_cut", dialogue_pairs)
        else:
            dialogue_pairs = []
            pair_stats = _build_pair_stats("timeout_no_pairs", dialogue_pairs)
    else:
        note_id_hint = extract_note_id(input_url) or "?"
        print(f"    [stage] note={note_id_hint} open_comments_panel", flush=True)
        open_comments_panel(page, rounds=3)
        try_prefer_hot_comments(page)

        no_comment_marker = detect_no_comment_marker(page)
        if no_comment_marker and not fast_api_selected:
            dialogue_pairs = []
            pair_stats = _build_pair_stats("no_comment_marker", dialogue_pairs, {"no_comment_marker": no_comment_marker})
        else:
            expand_budget_sec = max(2.0, min(18.0, _remaining_hard_sec() - 4.0))
            if expand_budget_sec > 2.0:
                print(f"    [stage] note={note_id_hint} expand_comments budget={expand_budget_sec:.1f}s", flush=True)
                expand_comments_for_capture(
                    page,
                    rounds=max(2, int(expand_rounds_per_note)),
                    sleep_ms=650,
                    note_hint=note_id_hint,
                    verbose=True,
                    max_seconds=expand_budget_sec,
                )
                page.wait_for_timeout(700)

            valid_api = _select_api_pairs(threshold)
            if valid_api:
                dialogue_pairs = valid_api
                pair_stats = _build_pair_stats("api", dialogue_pairs)
            elif not enable_dom_fallback or float(dom_fallback_max_seconds) <= 0:
                # 默认禁用 DOM 兜底，避免长时间卡在复杂评论树解析。
                relaxed_api = _select_api_pairs(0)
                if relaxed_api:
                    dialogue_pairs = relaxed_api
                    pair_stats = _build_pair_stats("api_relaxed_no_dom", dialogue_pairs)
                else:
                    dialogue_pairs = []
                    pair_stats = _build_pair_stats("no_pairs_no_dom", dialogue_pairs)
            else:
                dom_budget_sec = max(0.0, min(float(dom_fallback_max_seconds), _remaining_hard_sec() - 1.2))
                if dom_budget_sec < 1.5:
                    relaxed_api = _select_api_pairs(0)
                    if relaxed_api:
                        dialogue_pairs = relaxed_api
                        pair_stats = _build_pair_stats("api_relaxed_budget", dialogue_pairs)
                    else:
                        dialogue_pairs = []
                        pair_stats = _build_pair_stats("budget_no_pairs", dialogue_pairs)
                else:
                    print(f"    [dom] note={note_id_hint} start budget={dom_budget_sec:.1f}s", flush=True)
                    dom_payload = collect_comment_reply_pairs(
                        page,
                        max_pairs=max_comments,
                        min_reply_likes=min_comment_likes,
                        max_parents=max(1, int(max_parents_per_note)),
                        expand_wait_ms=420,
                        max_depth=max(1, int(max_reply_depth)),
                        time_budget_sec=dom_budget_sec,
                    )
                    dialogue_pairs = [
                        p for p in dom_payload.get("pairs", []) if _is_valid_dialogue_output(p.get("output", "") or "")
                    ]
                    dialogue_pairs = _dedupe_pairs(dialogue_pairs, max_comments)

                    if not dialogue_pairs:
                        relaxed_api = _select_api_pairs(0)
                        if relaxed_api:
                            dialogue_pairs = relaxed_api
                            pair_stats = _build_pair_stats("api_relaxed_low_like", dialogue_pairs)
                        else:
                            dialogue_pairs = []
                            pair_stats = _build_pair_stats(
                                str((dom_payload.get("stats") or {}).get("selection_mode") or "no_pairs"),
                                dialogue_pairs,
                                {
                                    "dom_time_budget_sec": round(dom_budget_sec, 2),
                                    "max_thread_depth_seen": int(
                                        ((dom_payload.get("stats") or {}).get("max_thread_depth_seen", 0) or 0)
                                    ),
                                },
                            )
                    else:
                        pair_stats = _build_pair_stats(
                            "reply_pairs",
                            dialogue_pairs,
                            {
                                "dom_time_budget_sec": round(dom_budget_sec, 2),
                                "max_thread_depth_seen": int(
                                    ((dom_payload.get("stats") or {}).get("max_thread_depth_seen", 1) or 1)
                                ),
                            },
                        )
                    print(f"    [dom] note={note_id_hint} done pairs={len(dialogue_pairs)}", flush=True)

    pair_stats["note_elapsed_sec"] = round(_elapsed_sec(), 2)

    item = {
        "platform": "xiaohongshu",
        "url": input_url,
        "dialogue_pairs": dialogue_pairs,
        "pair_stats": pair_stats,
        "fetch_meta": {
            "input_url": input_url,
            "final_url": final_url or input_url,
            "http_status": status,
        },
        "collected_at": datetime.utcnow().isoformat() + "Z",
    }
    try:
        item["fetch_meta"]["page_title"] = (page.title() or "").strip()
    except Exception:
        pass
    try:
        body = (page.text_content("body") or "").strip()
        item["fetch_meta"]["body_head"] = _truncate(body, 400)
    except Exception:
        pass
    return item


def collect_note_via_goto(
    page,
    url: str,
    max_comments: int,
    sleep_sec: float,
    min_comment_likes: int,
    page_timeout_ms: int,
    max_parents_per_note: int,
    expand_rounds_per_note: int,
    max_reply_depth: int,
    note_soft_timeout_sec: float = 45.0,
    note_hard_timeout_sec: float = 120.0,
    dom_fallback_max_seconds: float = 8.0,
    enable_dom_fallback: bool = False,
) -> Dict[str, Any]:
    api_pairs: List[Dict[str, Any]] = []

    def on_resp(resp):
        try:
            api_pairs.extend(_parse_comment_api_response(resp, max_depth=max_reply_depth))
        except Exception:
            pass

    listener_added = False
    try:
        page.on("response", on_resp)
        listener_added = True
    except Exception:
        listener_added = False

    status = 0
    stage = "goto"
    try:
        print(f"    [stage] note={extract_note_id(url) or '?'} goto_detail", flush=True)
        response = page.goto(url, timeout=page_timeout_ms, wait_until="domcontentloaded")
        try:
            status = int(response.status) if response else 0
        except Exception:
            status = 0
        stage = "collect_detail"
        return collect_note_from_current_page(
            page=page,
            input_url=url,
            max_comments=max_comments,
            sleep_sec=sleep_sec,
            min_comment_likes=min_comment_likes,
            page_timeout_ms=page_timeout_ms,
            api_pairs=api_pairs,
            max_parents_per_note=max_parents_per_note,
            expand_rounds_per_note=expand_rounds_per_note,
            max_reply_depth=max_reply_depth,
            status=status,
            note_soft_timeout_sec=note_soft_timeout_sec,
            note_hard_timeout_sec=note_hard_timeout_sec,
            dom_fallback_max_seconds=dom_fallback_max_seconds,
            enable_dom_fallback=enable_dom_fallback,
        )
    except Exception as exc:
        item = build_unavailable_item(url, min_comment_likes, "goto_or_collect_error")
        item["fetch_meta"]["http_status"] = status
        try:
            item["fetch_meta"]["final_url"] = (page.url or "").strip()
        except Exception:
            item["fetch_meta"]["final_url"] = url
        item["fetch_meta"]["error_stage"] = stage
        item["fetch_meta"]["error"] = _truncate(str(exc), 320)
        item["fetch_meta"]["traceback"] = _truncate(traceback.format_exc(), 3000)
        print(
            f"[note-goto-fail] stage={stage} note={extract_note_id(url) or '?'} "
            f"error={_truncate(str(exc), 220)}",
            flush=True,
        )
        print(traceback.format_exc(), flush=True)
        return item
    finally:
        if listener_added:
            try:
                page.remove_listener("response", on_resp)
            except Exception:
                pass


def collect_visible_note_cards(
    page,
    max_cards: int,
    allow_explore_fallback: bool,
    min_card_comment_hint: int = 0,
    min_card_like_hint: int = 0,
    source_mode: str = "keyword",
) -> List[Dict[str, Any]]:
    if source_mode == "explore":
        selectors = ['a[href*="/explore/"]', 'a[href*="/discovery/item/"]', 'a[href*="/search_result/"]']
    else:
        selectors = ['a[href*="/search_result/"]']
    if allow_explore_fallback and source_mode != "explore":
        selectors += ['a[href*="/explore/"]', 'a[href*="/discovery/item/"]']
    query = ", ".join(selectors)
    try:
        anchors = page.query_selector_all(query)
    except Exception:
        anchors = []

    seen_ids: Set[str] = set()
    cards: List[Dict[str, Any]] = []
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
        except Exception:
            continue
        if not href:
            continue
        full = href if href.startswith("http") else f"https://www.xiaohongshu.com{href}"
        full = normalize_url(full)
        if "/search_result?" in full and "/search_result/" not in full:
            continue
        if "xiaohongshu.com" not in full:
            continue
        nid = extract_note_id(full)
        if not nid or nid in seen_ids:
            continue
        try:
            if hasattr(a, "is_visible") and not a.is_visible():
                continue
        except Exception:
            pass
        comment_hint, like_hint = extract_card_hints(a)
        # 如果能从卡片文案解析出“评论数”且明显偏低，则跳过，降低无效点击。
        if min_card_comment_hint > 0 and comment_hint >= 0 and comment_hint < min_card_comment_hint:
            continue
        # 点赞数可作为评论活跃度的先验信号：卡片点赞过低时可直接跳过，减少无效进详情点击。
        if min_card_like_hint > 0 and like_hint >= 0 and like_hint < min_card_like_hint:
            continue
        seen_ids.add(nid)
        cards.append(
            {
                "note_id": nid,
                "url": full,
                "element": a,
                "comment_hint": comment_hint,
                "like_hint": like_hint,
            }
        )
        if len(cards) >= max(1, int(max_cards)):
            break
    if source_mode == "explore":
        # explore 模式下更偏向热度：优先按点赞排序（评论提示经常不可得）
        cards.sort(key=lambda x: (int(x.get("like_hint", -1)), int(x.get("comment_hint", -1))), reverse=True)
    else:
        cards.sort(key=lambda x: (int(x.get("comment_hint", -1)), int(x.get("like_hint", -1))), reverse=True)
    return cards


def is_search_listing_url(url: str) -> bool:
    u = (url or "").lower()
    return "/search_result" in u and "keyword=" in u


def is_listing_page_url(url: str, source_mode: str) -> bool:
    if source_mode == "keyword":
        return is_search_listing_url(url)
    u = (url or "").lower()
    if "xiaohongshu.com" not in u:
        return False
    if "website-login/error" in u:
        return False
    # 详情页通常包含可提取的 note id；没有 note id 时，视为列表/发现页。
    return not bool(extract_note_id(u))


def wait_for_detail_or_block(page, previous_url: str, timeout_ms: int) -> bool:
    deadline = time.time() + max(2.0, timeout_ms / 1000.0)
    while time.time() < deadline:
        cur = ""
        try:
            cur = (page.url or "").strip()
        except Exception:
            cur = ""
        if detect_rate_limit_marker(page):
            return True
        if extract_note_id(cur):
            return True
        if cur != previous_url and not is_search_listing_url(cur):
            return True
        try:
            if page.query_selector("div.comment-item, .comment-item, .interaction-container, .note-content"):
                return True
        except Exception:
            pass
        page.wait_for_timeout(280)
    return False


def open_note_by_click(page, card: Dict[str, Any], page_timeout_ms: int, source_mode: str = "keyword") -> bool:
    prev_url = ""
    try:
        prev_url = (page.url or "").strip()
    except Exception:
        prev_url = ""
    el = card.get("element")
    if not el:
        return False
    try:
        el.scroll_into_view_if_needed(timeout=1200)
    except Exception:
        pass
    page.wait_for_timeout(180 + random.randint(0, 240))
    try:
        el.click(timeout=2500)
    except Exception:
        try:
            page.evaluate("(el) => el.click()", el)
        except Exception:
            return False
    return wait_for_detail_or_block(page, prev_url, min(16000, max(4500, int(page_timeout_ms))))


def collect_note_via_click(
    page,
    card: Dict[str, Any],
    max_comments: int,
    sleep_sec: float,
    min_comment_likes: int,
    page_timeout_ms: int,
    max_parents_per_note: int,
    expand_rounds_per_note: int,
    max_reply_depth: int,
    note_soft_timeout_sec: float = 45.0,
    note_hard_timeout_sec: float = 120.0,
    dom_fallback_max_seconds: float = 8.0,
    enable_dom_fallback: bool = False,
) -> Dict[str, Any]:
    api_pairs: List[Dict[str, Any]] = []

    def on_resp(resp):
        try:
            api_pairs.extend(_parse_comment_api_response(resp, max_depth=max_reply_depth))
        except Exception:
            pass

    listener_added = False
    try:
        page.on("response", on_resp)
        listener_added = True
    except Exception:
        listener_added = False

    stage = "click_open"
    try:
        opened = open_note_by_click(page, card, page_timeout_ms)
        if not opened:
            marker = detect_rate_limit_marker(page)
            reason = "rate_limited" if marker else "click_open_failed"
            item = build_unavailable_item(card.get("url", ""), min_comment_likes, reason)
            try:
                item["fetch_meta"]["final_url"] = (page.url or "").strip()
            except Exception:
                pass
            if marker:
                item["fetch_meta"]["rate_limit_marker"] = marker
            return item
        stage = "collect_detail"
        return collect_note_from_current_page(
            page=page,
            input_url=card.get("url", ""),
            max_comments=max_comments,
            sleep_sec=sleep_sec,
            min_comment_likes=min_comment_likes,
            page_timeout_ms=page_timeout_ms,
            api_pairs=api_pairs,
            max_parents_per_note=max_parents_per_note,
            expand_rounds_per_note=expand_rounds_per_note,
            max_reply_depth=max_reply_depth,
            status=0,
            note_soft_timeout_sec=note_soft_timeout_sec,
            note_hard_timeout_sec=note_hard_timeout_sec,
            dom_fallback_max_seconds=dom_fallback_max_seconds,
            enable_dom_fallback=enable_dom_fallback,
        )
    except Exception as exc:
        item = build_unavailable_item(card.get("url", ""), min_comment_likes, "click_or_collect_error")
        try:
            item["fetch_meta"]["final_url"] = (page.url or "").strip()
        except Exception:
            item["fetch_meta"]["final_url"] = card.get("url", "")
        item["fetch_meta"]["error_stage"] = stage
        item["fetch_meta"]["error"] = _truncate(str(exc), 320)
        item["fetch_meta"]["traceback"] = _truncate(traceback.format_exc(), 3000)
        print(
            f"[note-click-fail] stage={stage} note={card.get('note_id', '?')} "
            f"error={_truncate(str(exc), 220)}",
            flush=True,
        )
        print(traceback.format_exc(), flush=True)
        return item
    finally:
        if listener_added:
            try:
                page.remove_listener("response", on_resp)
            except Exception:
                pass


def back_to_search_page(page, search_url: str, page_timeout_ms: int, source_mode: str = "keyword") -> bool:
    cur = ""
    try:
        cur = (page.url or "").strip()
    except Exception:
        cur = ""
    if is_listing_page_url(cur, source_mode):
        return True
    for _ in range(2):
        try:
            page.go_back(timeout=min(12000, max(2500, int(page_timeout_ms))), wait_until="domcontentloaded")
        except Exception as exc:
            if _looks_like_driver_disconnected(exc):
                raise
        try:
            page.wait_for_timeout(650)
        except Exception as exc:
            if _looks_like_driver_disconnected(exc):
                raise
        try:
            cur = (page.url or "").strip()
        except Exception:
            cur = ""
        if is_listing_page_url(cur, source_mode):
            return True
    try:
        page.goto(search_url, timeout=page_timeout_ms, wait_until="domcontentloaded")
        try:
            page.wait_for_timeout(1000)
        except Exception as exc:
            if _looks_like_driver_disconnected(exc):
                raise
        return True
    except Exception:
        return False


@dataclass
class RunCounters:
    processed_notes: int = 0
    kept_notes: int = 0
    kept_pairs: int = 0
    kept_high_like_pairs: int = 0
    dropped_unavailable: int = 0
    dropped_rate_limited: int = 0
    dropped_short: int = 0
    dropped_high_like: int = 0
    dropped_ads: int = 0
    failed: int = 0
    consecutive_rate_limited: int = 0


def _checkpoint_path(output: Path) -> Path:
    return output.parent / (output.stem + ".checkpoint.json")


def load_keyword_checkpoint(output: Path) -> int:
    """返回上次完成的关键词索引（0-based），未找到则返回 -1。"""
    path = _checkpoint_path(output)
    if not path.exists():
        return -1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return int(data.get("last_completed_keyword_index", -1))
    except Exception:
        return -1


def save_keyword_checkpoint(output: Path, kw_index: int, kw: str) -> None:
    path = _checkpoint_path(output)
    try:
        path.write_text(
            json.dumps(
                {
                    "last_completed_keyword_index": kw_index,
                    "last_keyword": kw,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def load_seen_state(output: Path) -> tuple[Set[str], int, int]:
    seen_ids: Set[str] = set()
    kept_notes = 0
    kept_pairs = 0
    if not output.exists():
        return seen_ids, kept_notes, kept_pairs
    for line in output.open("r", encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        candidate_url = (obj.get("url") or (obj.get("fetch_meta", {}) or {}).get("final_url") or "").strip()
        nid = extract_note_id(candidate_url)
        if nid:
            seen_ids.add(nid)
        pairs = obj.get("dialogue_pairs") or []
        if pairs:
            kept_notes += 1
            kept_pairs += len(pairs)
    return seen_ids, kept_notes, kept_pairs


def decide_drop_reason(item: Dict[str, Any], args) -> str:
    pair_stats = item.get("pair_stats", {}) or {}
    pairs = item.get("dialogue_pairs") or []
    if "dialogue_pairs" not in item:
        return "unavailable"
    if pair_stats.get("selection_mode") == "unavailable":
        return str(pair_stats.get("unavailable_reason") or "unavailable")
    if not pairs:
        return "no_pairs"
    if args.strict_high_like:
        high_like_num = int(pair_stats.get("high_like_pairs", 0) or 0)
        if high_like_num < args.min_liked_comments_per_note:
            return "high_like_insufficient"
    if args.drop_ads:
        joined = " ".join(((p.get("input", "") or "") + " " + (p.get("output", "") or "")) for p in pairs[:5])
        if looks_like_ad(joined):
            return "ad_like"
    return ""


def maybe_log_debug_record(
    page,
    args,
    debug_counts: Dict[str, int],
    debug_events_path: Path,
    record_key: str,
    record: Dict[str, Any],
) -> None:
    if not args.debug:
        return
    limit = max(1, int(args.debug_max))
    debug_counts.setdefault(record_key, 0)
    if debug_counts[record_key] >= limit:
        return
    debug_counts[record_key] += 1
    try:
        Path(args.debug_dir).mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.utcnow().isoformat() + "Z", **record}
        with debug_events_path.open("a", encoding="utf-8") as df:
            df.write(json.dumps(rec, ensure_ascii=False) + "\n")
        tag = _safe_name(f"{record.get('idx', 'x')}_{record_key}")
        if args.debug_save_screenshot:
            page.screenshot(path=str(Path(args.debug_dir) / f"{tag}.png"), full_page=True)
        if args.debug_save_html:
            (Path(args.debug_dir) / f"{tag}.html").write_text(page.content(), encoding="utf-8")
    except Exception:
        pass


def summarize_pairs(pairs: List[Dict[str, Any]]) -> tuple[str, int]:
    source_counts: Dict[str, int] = {}
    max_depth = 0
    for p in pairs:
        src = str(p.get("source") or "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1
        try:
            d = int(p.get("thread_depth", 1) or 1)
        except Exception:
            d = 1
        if d > max_depth:
            max_depth = d
    parts = [f"{k}:{source_counts[k]}" for k in sorted(source_counts.keys())]
    return ",".join(parts) if parts else "none", max_depth


def apply_item_result(
    item: Dict[str, Any],
    args,
    counters: RunCounters,
    out_file,
    idx: int,
    total_cap: int,
    input_url: str,
    page,
    debug_counts: Dict[str, int],
    debug_events_path: Path,
) -> str:
    pair_stats = item.get("pair_stats", {}) or {}
    pairs = item.get("dialogue_pairs") or []
    pairs_cnt = len(pairs)
    high_like_pairs = int(pair_stats.get("high_like_pairs", 0) or 0)
    drop_reason = decide_drop_reason(item, args)
    final_seen_url = _truncate((item.get("fetch_meta", {}) or {}).get("final_url", ""), 140)
    pair_src_summary, pair_max_depth = summarize_pairs(pairs)

    if drop_reason:
        marker = (item.get("fetch_meta", {}) or {}).get("rate_limit_marker", "")
        if drop_reason == "rate_limited":
            counters.dropped_rate_limited += 1
        elif drop_reason in ("unavailable", "redirect_404", "page_marker", "click_open_failed") or drop_reason.startswith("http_"):
            counters.dropped_unavailable += 1
        elif drop_reason in ("no_pairs", "short_content"):
            counters.dropped_short += 1
        elif drop_reason == "high_like_insufficient":
            counters.dropped_high_like += 1
        elif drop_reason == "ad_like":
            counters.dropped_ads += 1
        else:
            counters.dropped_unavailable += 1

        maybe_log_debug_record(
            page=page,
            args=args,
            debug_counts=debug_counts,
            debug_events_path=debug_events_path,
            record_key=drop_reason,
            record={
                "idx": idx,
                "drop_reason": drop_reason,
                "input_url": input_url,
                "final_url": (item.get("fetch_meta", {}) or {}).get("final_url", ""),
                "http_status": (item.get("fetch_meta", {}) or {}).get("http_status", 0),
                "pairs_count": pairs_cnt,
                "high_like_pairs": high_like_pairs,
                "like_signal_found": bool(pair_stats.get("like_signal_found", False)),
                "rate_limit_marker": (item.get("fetch_meta", {}) or {}).get("rate_limit_marker", ""),
            },
        )
        print(
            f"[note {idx}/{total_cap}] DROP reason={drop_reason} "
            f"pairs={pairs_cnt} high_like={high_like_pairs} "
            f"mode={pair_stats.get('selection_mode', '')} marker={_truncate(str(marker), 60)} "
            f"final={final_seen_url}"
        )
        return drop_reason

    out_file.write(json.dumps(item, ensure_ascii=False) + "\n")
    out_file.flush()
    counters.kept_notes += 1
    counters.kept_pairs += pairs_cnt
    counters.kept_high_like_pairs += high_like_pairs
    print(
        f"[note {idx}/{total_cap}] KEEP pairs={pairs_cnt} "
        f"high_like={high_like_pairs} src={pair_src_summary} depth_max={pair_max_depth} "
        f"final={final_seen_url}"
    )
    return ""


def print_progress(counters: RunCounters, max_total_notes: int) -> None:
    print(
        "progress: "
        f"notes={counters.processed_notes}/{max_total_notes}, "
        f"kept_notes={counters.kept_notes}, kept_pairs={counters.kept_pairs}, "
        f"kept_high_like_pairs={counters.kept_high_like_pairs}, "
        f"drop_unavailable={counters.dropped_unavailable}, "
        f"drop_rate_limited={counters.dropped_rate_limited}, "
        f"drop_short={counters.dropped_short}, "
        f"drop_high_like={counters.dropped_high_like}, "
        f"drop_ads={counters.dropped_ads}, failed={counters.failed}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="XHS comment-reply collector (scenario-tuned: click detail -> collect dialogue pairs)."
    )
    parser.add_argument("--keywords-file", type=str, default="training/data/raw/keywords.txt")
    parser.add_argument(
        "--source-mode",
        type=str,
        choices=["keyword", "explore"],
        default="keyword",
        help="候选帖子来源模式：keyword=按关键词搜索（默认）；explore=按发现/推荐流抓取。",
    )
    parser.add_argument(
        "--explore-entry-url",
        type=str,
        default="https://www.xiaohongshu.com/explore",
        help="source-mode=explore 时的入口列表页 URL。",
    )
    parser.add_argument(
        "--keyword-start-idx",
        type=int,
        default=1,
        help="仅处理关键词文件中的区间（1-based，包含）。默认 1 表示从第一个关键词开始。",
    )
    parser.add_argument(
        "--keyword-end-idx",
        type=int,
        default=0,
        help="仅处理关键词文件中的区间（1-based，包含）。0 表示处理到最后一个关键词。",
    )
    parser.add_argument("--url-file", type=str, default="")
    parser.add_argument("--output", type=str, default="")

    parser.add_argument("--target-pairs", type=int, default=1200, help="Stop when kept dialogue pairs reach this target.")
    parser.add_argument(
        "--target-pairs-per-keyword",
        type=int,
        default=180,
        help="Switch to next keyword once this many kept pairs are added for current keyword. <=0 disables.",
    )
    parser.add_argument("--max-notes-per-keyword", type=int, default=80, help="Max note open attempts per keyword.")
    parser.add_argument("--max-total-notes", type=int, default=1200, help="Global cap of note open attempts.")
    parser.add_argument("--max-total-urls", type=int, default=0, help="Legacy alias of --max-total-notes.")
    parser.add_argument("--max-cards-per-round", type=int, default=80, help="How many visible cards to scan each round.")
    parser.add_argument(
        "--max-scroll-rounds",
        type=int,
        default=50,
        help="连续滚动多少轮仍无新卡片则切换关键词，默认 50（原 20 偏低易过早放弃）。",
    )
    parser.add_argument(
        "--scroll-wait-ms",
        type=int,
        default=1200,
        help="每次滚动后等待(ms)，给页面懒加载时间，默认 1200。",
    )
    parser.add_argument(
        "--min-card-comment-hint",
        type=int,
        default=0,
        help="卡片文本若能识别到评论数且低于该阈值则跳过；默认 0 表示不依赖卡片评论数（适配评论数不展示场景）。",
    )
    parser.add_argument(
        "--min-card-like-hint",
        type=int,
        default=0,
        help="卡片点赞数预过滤阈值。>0 时优先点击高点赞帖子（评论活跃度通常更高）。",
    )
    parser.add_argument(
        "--unknown-like-keep-prob",
        type=float,
        default=0.15,
        help="当卡片无法解析点赞数(like_hint<0)时的保留概率（0~1）。",
    )
    parser.add_argument(
        "--worker-id",
        type=int,
        default=0,
        help="并行分片 worker id（从 0 开始）。与 --worker-count 一起用于 A/B 去重分片。",
    )
    parser.add_argument(
        "--worker-count",
        type=int,
        default=1,
        help="并行分片总 worker 数；1 表示不分片。",
    )

    parser.add_argument("--allow-explore-fallback", action="store_true", help="Also allow /explore and /discovery/item cards.")
    parser.add_argument("--max-comments", type=int, default=20, help="Max dialogue pairs retained per note.")
    parser.add_argument("--max-parents-per-note", type=int, default=50, help="Max parent comments to inspect in one note.")
    parser.add_argument("--expand-rounds-per-note", type=int, default=12, help="Expand/load-more rounds per note.")
    parser.add_argument("--max-reply-depth", type=int, default=3, help="Max nested reply depth to keep (API preferred).")
    parser.add_argument("--min-comment-likes", type=int, default=8, help="Minimum likes for reply side when like signal exists.")
    parser.add_argument("--strict-high-like", action="store_true", help="Drop notes with insufficient high-like pairs.")
    parser.add_argument("--min-liked-comments-per-note", type=int, default=1, help="Used with --strict-high-like.")
    parser.add_argument("--drop-ads", action="store_true", help="Drop ad-like samples.")

    parser.add_argument("--page-timeout-ms", type=int, default=50000)
    parser.add_argument(
        "--default-operation-timeout-ms",
        type=int,
        default=60000,
        help="Playwright 单步操作最大等待(ms)，防止长时间卡死，默认 60s。",
    )
    parser.add_argument("--progress-every", type=int, default=10)
    parser.add_argument("--sleep-sec", type=float, default=2.0, help="Base sleep between note attempts.")
    parser.add_argument("--sleep-jitter-sec", type=float, default=1.3, help="Random additional sleep.")
    parser.add_argument("--keyword-cooldown-sec", type=float, default=3.0, help="Pause when switching keywords.")
    parser.add_argument(
        "--keyword-pass-limit",
        type=int,
        default=1,
        help="关键词区间整体循环的轮次上限。1 表示只跑一遍；0 表示无限循环直到达到 --target-pairs。",
    )
    parser.add_argument(
        "--keyword-pass-sleep-sec",
        type=float,
        default=120.0,
        help="当完成一整轮关键词区间但未达到 --target-pairs 时，下一轮开始前的休眠秒数。",
    )
    parser.add_argument("--max-consecutive-rate-limited", type=int, default=6, help="Cooldown trigger threshold.")
    parser.add_argument("--cooldown-sec", type=float, default=180.0, help="Cooldown duration after repeated rate-limit.")
    parser.add_argument(
        "--rate-limit-exit-sec",
        type=float,
        default=1800.0,
        help="触发连续风控后直接退出，并建议冷却秒数（配合监督器可自动长冷却重启）。0 表示不退出只 sleep。",
    )
    parser.add_argument(
        "--self-restart-every-notes",
        type=int,
        default=120,
        help="每处理这么多 note（attempt）后自退出一次，让监督器重启以释放 Playwright driver 内存。<=0 禁用。",
    )
    parser.add_argument(
        "--note-soft-timeout-sec",
        type=float,
        default=45.0,
        help="单帖子软预算秒数：若已拿到可用 API 对话对，超时后提前收敛。",
    )
    parser.add_argument(
        "--note-hard-timeout-sec",
        type=float,
        default=120.0,
        help="单帖子硬预算秒数：超过后强制切下一帖，防止卡死。",
    )
    parser.add_argument(
        "--dom-fallback-max-seconds",
        type=float,
        default=8.0,
        help="DOM 兜底解析最大秒数（API 不足时）。设为 0 可关闭 DOM 兜底。",
    )
    parser.add_argument(
        "--enable-dom-fallback",
        action="store_true",
        help="启用 DOM 兜底评论解析（默认关闭以避免长时间卡在复杂评论树）。",
    )
    parser.add_argument(
        "--keyword-note-open-mode",
        type=str,
        choices=["goto", "click"],
        default="goto",
        help="关键词模式打开笔记方式：goto(默认，更稳) 或 click。",
    )
    parser.add_argument(
        "--run-log-file",
        type=str,
        default="",
        help="运行日志文件（同时记录 stdout/stderr）；默认按输出文件自动命名。",
    )

    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--debug-dir", type=str, default="training/data/raw/xhs_debug")
    parser.add_argument("--debug-max", type=int, default=20, help="Max debug events per reason.")
    parser.add_argument("--debug-save-html", action="store_true")
    parser.add_argument("--debug-save-screenshot", action="store_true")
    parser.add_argument(
        "--verbose-note-log",
        action="store_true",
        help="Print extra verbose logs for note picking and keyword progress.",
    )

    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--skip-login", action="store_true")
    parser.add_argument(
        "--disable-storage-state",
        action="store_true",
        help="禁用 Playwright storage_state 的读取/保存：每次都走手动登录闸门（适合你希望始终扫码登录的场景）。",
    )
    parser.add_argument(
        "--storage-state-file",
        type=str,
        default="training/data/raw/xhs_auth_state.json",
        help="Playwright 登录态文件。存在时自动复用，首次手动登录后会写入该文件。",
    )
    parser.add_argument("--append", action="store_true", help="Append output and skip seen note IDs.")
    args = parser.parse_args()

    if args.max_total_urls > 0:
        args.max_total_notes = args.max_total_urls
    if args.max_notes_per_keyword <= 0:
        args.max_notes_per_keyword = 10**9
    if args.max_total_notes <= 0:
        args.max_total_notes = 10**9
    if args.target_pairs <= 0:
        args.target_pairs = 10**9
    if args.target_pairs_per_keyword <= 0:
        args.target_pairs_per_keyword = 10**9
    if args.max_scroll_rounds <= 0:
        args.max_scroll_rounds = 10**9
    if args.scroll_wait_ms <= 0:
        args.scroll_wait_ms = 1200
    if args.note_soft_timeout_sec <= 0:
        args.note_soft_timeout_sec = 45.0
    if args.note_hard_timeout_sec <= args.note_soft_timeout_sec:
        args.note_hard_timeout_sec = args.note_soft_timeout_sec + 8.0
    if args.dom_fallback_max_seconds < 0:
        args.dom_fallback_max_seconds = 0.0
    args.max_reply_depth = max(1, int(args.max_reply_depth))
    if args.self_restart_every_notes < 0:
        args.self_restart_every_notes = 0
    if args.rate_limit_exit_sec < 0:
        args.rate_limit_exit_sec = 0.0
    args.min_card_like_hint = max(0, int(args.min_card_like_hint))
    args.unknown_like_keep_prob = min(1.0, max(0.0, float(args.unknown_like_keep_prob)))
    args.worker_count = max(1, int(args.worker_count))
    args.worker_id = int(args.worker_id) % int(args.worker_count)
    args.source_mode = str(args.source_mode or "keyword").strip().lower()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = Path(args.output or f"training/data/raw/xhs_candidates_{ts}.jsonl")
    ensure_parent(output)
    run_log_path = Path(args.run_log_file) if args.run_log_file else output.parent / f"{output.stem}.run.log"
    setup_run_logging(run_log_path)
    print(f"[log] run_log={run_log_path}")
    print(
        f"[args] source_mode={args.source_mode} "
        f"worker={args.worker_id}/{args.worker_count} "
        f"min_card_like_hint={args.min_card_like_hint} "
        f"unknown_like_keep_prob={args.unknown_like_keep_prob} "
        f"explore_entry_url={_truncate(str(args.explore_entry_url), 80)}"
    )
    print(
        f"[args] rate_limit_exit_sec={args.rate_limit_exit_sec} "
        f"max_consecutive_rl={args.max_consecutive_rate_limited} "
        f"self_restart_every={args.self_restart_every_notes} "
        f"note_hard_timeout={args.note_hard_timeout_sec}s "
        f"headless={args.headless}"
    )

    keywords = read_lines(Path(args.keywords_file))
    if args.source_mode == "explore":
        # explore 模式不依赖关键词；保留一个虚拟关键词槽位复用主循环。
        keywords = ["__EXPLORE_FEED__"]
        kw_start0 = 0
        kw_end0 = 0
    else:
        kw_start0 = max(0, int(args.keyword_start_idx or 1) - 1)
        if int(args.keyword_end_idx or 0) <= 0:
            kw_end0 = max(0, len(keywords) - 1)
        else:
            kw_end0 = min(max(0, len(keywords) - 1), int(args.keyword_end_idx) - 1)
        if keywords and kw_start0 > kw_end0:
            raise SystemExit(
                f"关键词区间非法：--keyword-start-idx={args.keyword_start_idx} > --keyword-end-idx={args.keyword_end_idx}。"
            )
    direct_urls = [normalize_url(u) for u in read_lines(Path(args.url_file))] if args.url_file else []
    if args.source_mode == "keyword" and not keywords and not direct_urls:
        raise SystemExit(
            "未找到关键词或直链 URL。\n"
            f"- 请准备关键词文件: {args.keywords_file}\n"
            "  或者使用 --url-file 指定笔记 URL 列表。"
        )

    print("=== 安全提示 ===")
    print("1) 本脚本只读采集，不包含发帖/评论/点赞/关注。")
    print("2) 请遵守平台规则与当地法律，控制频率，避免过量抓取。")
    print("3) 输出仅用于学习与研究，后续请做脱敏和语义改写。")
    print("================")

    counters = RunCounters()
    seen_note_ids: Set[str] = set()
    if args.append and output.exists():
        seen_note_ids, old_notes, old_pairs = load_seen_state(output)
        counters.kept_notes = old_notes
        counters.kept_pairs = old_pairs
        print(f"[append] 已有 kept_notes={old_notes}, kept_pairs={old_pairs}, seen_note_ids={len(seen_note_ids)}")

    hb_every = max(1, int(args.progress_every))
    debug_counts: Dict[str, int] = {}
    debug_events_path = Path(args.debug_dir) / "debug_events.jsonl"
    file_mode = "a" if (args.append and output.exists()) else "w"
    storage_state_path: Optional[Path] = (
        None
        if args.disable_storage_state
        else (Path(args.storage_state_file).expanduser() if args.storage_state_file else None)
    )

    with sync_playwright() as p:
        global _pw_browser, _pw_context
        browser = p.chromium.launch(headless=args.headless)
        _pw_browser = browser
        context = None
        auth_state_loaded = False
        if storage_state_path and storage_state_path.exists():
            try:
                context = browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    storage_state=str(storage_state_path),
                )
                auth_state_loaded = True
                print(f"[auth] 已加载登录态: {storage_state_path}")
            except Exception as exc:
                print(f"[auth] 加载登录态失败，回退手动登录: {_truncate(str(exc), 220)}")
                context = None
        if context is None:
            context = browser.new_context(viewport={"width": 1440, "height": 900})
        _pw_context = context
        page = context.new_page()
        # 全局操作超时，防止单步（如 wait_for_selector）无限等待导致长时间卡死
        page.set_default_timeout(args.default_operation_timeout_ms)
        page.set_default_navigation_timeout(min(90000, args.default_operation_timeout_ms * 2))

        # 手动登录闸门：
        # 只要未显式指定 --skip-login，就先停在首页等待人工登录确认，避免未登录状态下乱搜导致二维码反复刷新。
        if not args.skip_login:
            try:
                page.goto("https://www.xiaohongshu.com", timeout=60000, wait_until="domcontentloaded")
            except Exception as exc:
                print(f"[auth] 打开首页失败: {_truncate(str(exc), 220)}")
            if auth_state_loaded:
                print("[auth] 已加载登录态，但仍进入手动登录确认模式（防止登录态失效导致乱搜）。")
            else:
                print("[auth] 未检测到可用登录态，进入手动登录模式。")
            print("请在当前浏览器页完成登录（不要关闭页面），完成后回到终端按 Enter 继续...")
            input()
            if storage_state_path:
                try:
                    ensure_parent(storage_state_path)
                    context.storage_state(path=str(storage_state_path))
                    print(f"[auth] 已保存登录态: {storage_state_path}")
                except Exception as exc:
                    print(f"[auth] 保存登录态失败: {_truncate(str(exc), 220)}")
        elif auth_state_loaded:
            print("[auth] --skip-login：复用已加载登录态。")
        else:
            print("[auth] --skip-login 且未加载登录态文件；若登录失效可能触发风控。")

        with output.open(file_mode, encoding="utf-8") as out_file:
            if direct_urls:
                print(f"[mode=url_file] 待处理 URL 数={len(direct_urls)}")
                for u in direct_urls:
                    if counters.processed_notes >= args.max_total_notes or counters.kept_pairs >= args.target_pairs:
                        break
                    nid = extract_note_id(u)
                    if nid and nid in seen_note_ids:
                        continue

                    counters.processed_notes += 1
                    idx = counters.processed_notes
                    if args.verbose_note_log:
                        print(
                            f"[pick direct] idx={idx} note_id={nid or 'unknown'} "
                            f"url={_truncate(u, 120)}"
                        )
                    try:
                        item = collect_note_via_goto(
                            page=page,
                            url=u,
                            max_comments=args.max_comments,
                            sleep_sec=args.sleep_sec,
                            min_comment_likes=args.min_comment_likes,
                            page_timeout_ms=args.page_timeout_ms,
                            max_parents_per_note=args.max_parents_per_note,
                            expand_rounds_per_note=args.expand_rounds_per_note,
                            max_reply_depth=args.max_reply_depth,
                            note_soft_timeout_sec=args.note_soft_timeout_sec,
                            note_hard_timeout_sec=args.note_hard_timeout_sec,
                            dom_fallback_max_seconds=args.dom_fallback_max_seconds,
                            enable_dom_fallback=args.enable_dom_fallback,
                        )
                        item["source_keywords"] = keywords[:]
                        drop_reason = apply_item_result(
                            item=item,
                            args=args,
                            counters=counters,
                            out_file=out_file,
                            idx=idx,
                            total_cap=args.max_total_notes,
                            input_url=u,
                            page=page,
                            debug_counts=debug_counts,
                            debug_events_path=debug_events_path,
                        )
                    except Exception as exc:
                        counters.failed += 1
                        cur_url = ""
                        try:
                            cur_url = (page.url or "").strip()
                        except Exception:
                            cur_url = ""
                        print(
                            f"[note {idx}/{args.max_total_notes}] FAIL error={_truncate(str(exc), 200)} "
                            f"input={_truncate(u, 120)} current={_truncate(cur_url, 120)}"
                        )
                        print(traceback.format_exc())
                        maybe_log_debug_record(
                            page=page,
                            args=args,
                            debug_counts=debug_counts,
                            debug_events_path=debug_events_path,
                            record_key="exception",
                            record={
                                "idx": idx,
                                "drop_reason": "exception",
                                "input_url": u,
                                "current_page_url": cur_url,
                                "error": str(exc)[:800],
                                "traceback": traceback.format_exc()[:2000],
                            },
                        )
                        drop_reason = "exception"

                    if nid:
                        seen_note_ids.add(nid)
                    if drop_reason == "rate_limited":
                        counters.consecutive_rate_limited += 1
                    else:
                        counters.consecutive_rate_limited = 0
                    if counters.consecutive_rate_limited >= args.max_consecutive_rate_limited:
                        print(
                            f"[guard] 连续风控 {counters.consecutive_rate_limited} 次。"
                            f"{'退出并长冷却' if args.rate_limit_exit_sec > 0 else '冷却后继续'}"
                        )
                        if args.rate_limit_exit_sec > 0:
                            print(
                                f"[guard] 建议冷却 {int(args.rate_limit_exit_sec)} 秒后再继续（exit_code={_EXIT_CODE_RATE_LIMIT}）。"
                            )
                            raise SystemExit(_EXIT_CODE_RATE_LIMIT)
                        time.sleep(max(0.0, args.cooldown_sec))
                        counters.consecutive_rate_limited = 0
                    if idx % hb_every == 0:
                        print_progress(counters, args.max_total_notes)
                    sleep_with_jitter(args.sleep_sec, args.sleep_jitter_sec)
                    if args.self_restart_every_notes > 0 and idx % int(args.self_restart_every_notes) == 0:
                        print(
                            f"[guard] 达到自重启阈值 idx={idx}（每 {args.self_restart_every_notes} notes），"
                            f"退出让监督器重启（exit_code={_EXIT_CODE_SELF_RESTART}）。"
                        )
                        raise SystemExit(_EXIT_CODE_SELF_RESTART)
            else:
                resume_from = 0
                if args.source_mode == "keyword" and args.append and output.exists():
                    last_done = load_keyword_checkpoint(output)
                    if last_done >= 0:
                        resume_from = last_done + 1
                        print(f"[append] 从关键词 #{resume_from + 1} 继续（已跑完前 {resume_from} 个）")
                resume_from = max(resume_from, kw_start0)
                print(
                    f"[mode={args.source_mode}] 关键词数={len(keywords)} "
                    f"kw_range={kw_start0 + 1}-{kw_end0 + 1} "
                    f"open_mode={args.keyword_note_open_mode} "
                    f"dom_fallback={'on' if args.enable_dom_fallback else 'off'} "
                    f"rate_limit_exit_sec={args.rate_limit_exit_sec} "
                    f"max_consecutive_rate_limited={args.max_consecutive_rate_limited} "
                    f"self_restart_every_notes={args.self_restart_every_notes}"
                )
                pass_no = 1
                while True:
                    if counters.processed_notes >= args.max_total_notes or counters.kept_pairs >= args.target_pairs:
                        break
                    any_kw_ran = False
                    for kw_idx, kw in enumerate(keywords):
                        if kw_idx < resume_from:
                            continue
                        if keywords and kw_idx > kw_end0:
                            break
                        if counters.processed_notes >= args.max_total_notes or counters.kept_pairs >= args.target_pairs:
                            break
                        any_kw_ran = True

                        kw_display = kw_idx + 1
                        kw_pairs_before = counters.kept_pairs
                        kw_notes_before = counters.kept_notes
                        listing_url = (
                            build_search_url(kw)
                            if args.source_mode == "keyword"
                            else normalize_url(args.explore_entry_url)
                        )
                        kw_label = kw if args.source_mode == "keyword" else f"explore_pass_{pass_no}"
                        print(f"[keyword {kw_display}/{len(keywords)}] {kw_label}")
                        try:
                            page.goto(listing_url, timeout=60000, wait_until="domcontentloaded")
                            page.wait_for_timeout(2300)
                        except Exception as exc:
                            print(f"[keyword={kw_label}] 打开列表页失败: {_truncate(str(exc), 220)}")
                            print(traceback.format_exc())
                            continue

                        attempts_this_kw = 0
                        scroll_round = 0
                        tried_in_kw: Set[str] = set()

                        while attempts_this_kw < args.max_notes_per_keyword:
                            kw_pairs_gained = counters.kept_pairs - kw_pairs_before
                            if counters.processed_notes >= args.max_total_notes or counters.kept_pairs >= args.target_pairs:
                                break
                            if kw_pairs_gained >= args.target_pairs_per_keyword:
                                print(
                                    f"[keyword={kw_label}] 达到关键词目标对话对 {kw_pairs_gained}/{args.target_pairs_per_keyword}，切换下一个关键词。"
                                )
                                break

                            cards = collect_visible_note_cards(
                                page=page,
                                max_cards=args.max_cards_per_round,
                                allow_explore_fallback=args.allow_explore_fallback,
                                min_card_comment_hint=args.min_card_comment_hint,
                                min_card_like_hint=args.min_card_like_hint,
                                source_mode=args.source_mode,
                            )
                            if args.verbose_note_log:
                                known_comment = sum(1 for c in cards if int(c.get("comment_hint", -1) or -1) >= 0)
                                known_like = sum(1 for c in cards if int(c.get("like_hint", -1) or -1) >= 0)
                                print(
                                    f"[cards] kw={kw_label} visible={len(cards)} "
                                    f"known_comment_hint={known_comment} known_like_hint={known_like}"
                                )

                            candidates: List[Dict[str, Any]] = []
                            for c in cards:
                                nid = c.get("note_id")
                                if not nid or nid in seen_note_ids or nid in tried_in_kw:
                                    continue
                                if args.worker_count > 1:
                                    slot = zlib.crc32(str(nid).encode("utf-8")) % int(args.worker_count)
                                    if slot != int(args.worker_id):
                                        continue
                                like_hint = int(c.get("like_hint", -1) or -1)
                                if args.min_card_like_hint > 0 and like_hint < 0:
                                    if random.random() > float(args.unknown_like_keep_prob):
                                        continue
                                candidates.append(c)

                            if not candidates:
                                scroll_round += 1
                                if scroll_round > args.max_scroll_rounds:
                                    print(f"[keyword={kw_label}] 无更多可用新卡片（已滚动 {scroll_round} 轮），切换关键词。")
                                    break
                                try:
                                    page.mouse.wheel(0, 1800)
                                    page.wait_for_timeout(args.scroll_wait_ms)
                                except Exception as _scroll_exc:
                                    if _looks_like_driver_disconnected(_scroll_exc):
                                        print("[guard] driver 断连（scroll），退出让监督器重启。")
                                        raise SystemExit(_EXIT_CODE_SELF_RESTART)
                                    print(f"[warn] scroll 异常（忽略）: {_truncate(str(_scroll_exc), 120)}")
                                continue

                            scroll_round = 0
                            card = candidates[0]
                            note_id = card.get("note_id", "")
                            input_url = card.get("url", "")
                            card_comment_hint = int(card.get("comment_hint", -1) or -1)
                            card_like_hint = int(card.get("like_hint", -1) or -1)
                            tried_in_kw.add(note_id)
                            attempts_this_kw += 1

                            counters.processed_notes += 1
                            idx = counters.processed_notes
                            if args.verbose_note_log:
                                print(
                                    f"[pick keyword] kw={kw_label} idx={idx} note_id={note_id} "
                                    f"card_comment_hint={card_comment_hint} card_like_hint={card_like_hint} "
                                    f"url={_truncate(input_url, 110)}"
                                )
                            try:
                                if args.keyword_note_open_mode == "goto":
                                    item = collect_note_via_goto(
                                        page=page,
                                        url=input_url,
                                        max_comments=args.max_comments,
                                        sleep_sec=args.sleep_sec,
                                        min_comment_likes=args.min_comment_likes,
                                        page_timeout_ms=args.page_timeout_ms,
                                        max_parents_per_note=args.max_parents_per_note,
                                        expand_rounds_per_note=args.expand_rounds_per_note,
                                        max_reply_depth=args.max_reply_depth,
                                        note_soft_timeout_sec=args.note_soft_timeout_sec,
                                        note_hard_timeout_sec=args.note_hard_timeout_sec,
                                        dom_fallback_max_seconds=args.dom_fallback_max_seconds,
                                        enable_dom_fallback=args.enable_dom_fallback,
                                    )
                                else:
                                    item = collect_note_via_click(
                                        page=page,
                                        card=card,
                                        max_comments=args.max_comments,
                                        sleep_sec=args.sleep_sec,
                                        min_comment_likes=args.min_comment_likes,
                                        page_timeout_ms=args.page_timeout_ms,
                                        max_parents_per_note=args.max_parents_per_note,
                                        expand_rounds_per_note=args.expand_rounds_per_note,
                                        max_reply_depth=args.max_reply_depth,
                                        note_soft_timeout_sec=args.note_soft_timeout_sec,
                                        note_hard_timeout_sec=args.note_hard_timeout_sec,
                                        dom_fallback_max_seconds=args.dom_fallback_max_seconds,
                                        enable_dom_fallback=args.enable_dom_fallback,
                                    )
                                item["source_keywords"] = [kw_label]
                                drop_reason = apply_item_result(
                                    item=item,
                                    args=args,
                                    counters=counters,
                                    out_file=out_file,
                                    idx=idx,
                                    total_cap=args.max_total_notes,
                                    input_url=input_url,
                                    page=page,
                                    debug_counts=debug_counts,
                                    debug_events_path=debug_events_path,
                                )
                            except Exception as exc:
                                counters.failed += 1
                                cur_url = ""
                                try:
                                    cur_url = (page.url or "").strip()
                                except Exception:
                                    cur_url = ""
                                print(
                                    f"[note {idx}/{args.max_total_notes}] FAIL error={_truncate(str(exc), 200)} "
                                    f"input={_truncate(input_url, 120)} current={_truncate(cur_url, 120)}"
                                )
                                print(traceback.format_exc())
                                maybe_log_debug_record(
                                    page=page,
                                    args=args,
                                    debug_counts=debug_counts,
                                    debug_events_path=debug_events_path,
                                    record_key="exception",
                                    record={
                                        "idx": idx,
                                        "drop_reason": "exception",
                                        "input_url": input_url,
                                        "current_page_url": cur_url,
                                        "error": str(exc)[:800],
                                        "traceback": traceback.format_exc()[:2000],
                                    },
                                )
                                drop_reason = "exception"

                            if note_id:
                                seen_note_ids.add(note_id)

                            cur_url = ""
                            try:
                                cur_url = (page.url or "").strip()
                            except Exception:
                                cur_url = ""
                            if not is_listing_page_url(cur_url, args.source_mode):
                                try:
                                    back_to_search_page(page, listing_url, args.page_timeout_ms, source_mode=args.source_mode)
                                except Exception as exc:
                                    if _looks_like_driver_disconnected(exc):
                                        print("[guard] driver 断连，退出让监督器重启。")
                                        raise SystemExit(_EXIT_CODE_SELF_RESTART)
                                    raise

                            if drop_reason == "rate_limited":
                                counters.consecutive_rate_limited += 1
                            else:
                                counters.consecutive_rate_limited = 0

                            if counters.consecutive_rate_limited >= args.max_consecutive_rate_limited:
                                print(
                                    f"[guard] 连续风控 {counters.consecutive_rate_limited} 次。"
                                    f"{'退出并长冷却' if args.rate_limit_exit_sec > 0 else '冷却后继续'}"
                                )
                                if args.rate_limit_exit_sec > 0:
                                    print(
                                        f"[guard] 建议冷却 {int(args.rate_limit_exit_sec)} 秒后再继续（exit_code={_EXIT_CODE_RATE_LIMIT}）。"
                                    )
                                    raise SystemExit(_EXIT_CODE_RATE_LIMIT)
                                time.sleep(max(0.0, args.cooldown_sec))
                                counters.consecutive_rate_limited = 0
                                try:
                                    page.goto(listing_url, timeout=args.page_timeout_ms, wait_until="domcontentloaded")
                                    page.wait_for_timeout(1700)
                                except Exception:
                                    pass

                            if idx % hb_every == 0:
                                print_progress(counters, args.max_total_notes)
                            if args.verbose_note_log:
                                kw_pairs_now = counters.kept_pairs - kw_pairs_before
                                print(
                                    f"[keyword progress] kw={kw_label} attempts={attempts_this_kw}/{args.max_notes_per_keyword} "
                                    f"pairs_gained={kw_pairs_now}/{args.target_pairs_per_keyword}"
                                )
                            sleep_with_jitter(args.sleep_sec, args.sleep_jitter_sec)
                            if args.self_restart_every_notes > 0 and idx % int(args.self_restart_every_notes) == 0:
                                print(
                                    f"[guard] 达到自重启阈值 idx={idx}（每 {args.self_restart_every_notes} notes），"
                                    f"退出让监督器重启（exit_code={_EXIT_CODE_SELF_RESTART}）。"
                                )
                                raise SystemExit(_EXIT_CODE_SELF_RESTART)

                        kw_pairs_after = counters.kept_pairs - kw_pairs_before
                        kw_notes_after = counters.kept_notes - kw_notes_before
                        print(
                            f"[keyword done] {kw_label} attempts={attempts_this_kw} "
                            f"kept_notes={kw_notes_after} kept_pairs={kw_pairs_after}"
                        )
                        if args.source_mode == "keyword":
                            save_keyword_checkpoint(output, kw_idx, kw)
                        if counters.processed_notes >= args.max_total_notes or counters.kept_pairs >= args.target_pairs:
                            break
                        time.sleep(max(0.0, args.keyword_cooldown_sec))

                    if counters.processed_notes >= args.max_total_notes or counters.kept_pairs >= args.target_pairs:
                        break
                    if not any_kw_ran:
                        break
                    if int(args.keyword_pass_limit) > 0 and pass_no >= int(args.keyword_pass_limit):
                        print(
                            f"[pass] 已完成 {pass_no} 轮关键词区间，未达到 target_pairs={args.target_pairs}，停止。"
                        )
                        break
                    pass_no += 1
                    print(
                        f"[pass] 完成一轮关键词区间但未达目标：kept_pairs={counters.kept_pairs}/{args.target_pairs}。"
                        f"休眠 {int(args.keyword_pass_sleep_sec)}s 后开始第 {pass_no} 轮。"
                    )
                    if args.source_mode == "keyword":
                        save_keyword_checkpoint(output, kw_start0 - 1, "__pass_restart__")
                    resume_from = kw_start0
                    time.sleep(max(0.0, float(args.keyword_pass_sleep_sec)))

        context.close()
        browser.close()

    print(
        "Done. "
        f"output={output} "
        f"processed_notes={counters.processed_notes} "
        f"kept_notes={counters.kept_notes} "
        f"kept_pairs={counters.kept_pairs} "
        f"kept_high_like_pairs={counters.kept_high_like_pairs} "
        f"drop_unavailable={counters.dropped_unavailable} "
        f"drop_rate_limited={counters.dropped_rate_limited} "
        f"drop_short={counters.dropped_short} "
        f"drop_high_like={counters.dropped_high_like} "
        f"drop_ads={counters.dropped_ads} "
        f"failed={counters.failed}"
    )
    global _RUN_LOG_FP
    if _RUN_LOG_FP is not None:
        try:
            _RUN_LOG_FP.flush()
            _RUN_LOG_FP.close()
        except Exception:
            pass
        _RUN_LOG_FP = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted by user. 已写入的数据已落盘；可使用 --append 继续。")
        raise SystemExit(130)
    except Exception:
        print("[fatal] 未捕获异常，详情如下：")
        print(traceback.format_exc())
        raise SystemExit(1)

