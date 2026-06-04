"""
l10n 语言支持模块 — 中英文双语言
==================================

提供 L10n frozen dataclass 管理所有 UI 字符串,
detect_language() 自动检测系统语言,
get_l10n() 工厂函数按语言返回对应字符串表。

创建日期: 2026-06-04
迭代: v1.0
"""

from __future__ import annotations

import locale
from dataclasses import dataclass


@dataclass(frozen=True)
class L10n:
    lang: str = "en"
    title: str = "⚜  SYSTEM  ⚜"
    initializing: str = "◆  INITIALIZING"
    connecting: str = "◆  CONNECTING  ● {user}@{host}:{port} ({os})"
    step_fmt: str = "────  STEP {n}/{total}  ({pct}%)  ────"
    all_done: str = "✓ All operations completed."
    error_prefix: str = "✗ {msg}"
    log_info: str = ">> {msg}"
    log_cmd: str = "$ {msg}"
    log_remote: str = "{text}"
    log_error: str = "LOG: {path}"
    step_pending: str = "⏳"
    step_running: str = "⟳"
    step_done: str = "✅"
    step_error: str = "❌"
    status_running: str = "Executing..."
    status_pending: str = "Waiting..."


_ZH: dict[str, str] = {
    "lang": "zh",
    "title": "⚜  系统  ⚜",
    "initializing": "◆ 初始化中",
    "connecting": "◆ 连接中  ● {user}@{host}:{port} ({os})",
    "step_fmt": "────  步骤 {n}/{total}  ({pct}%)  ────",
    "all_done": "✓ 所有操作已完成",
    "error_prefix": "✗ {msg}",
    "log_info": ">> {msg}",
    "log_cmd": "$ {msg}",
    "log_remote": "{text}",
    "log_error": "日志: {path}",
    "step_pending": "⏳",
    "step_running": "⟳",
    "step_done": "✅",
    "step_error": "❌",
    "status_running": "执行中...",
    "status_pending": "等待中...",
}


def detect_language() -> str:
    """Detect UI language. Returns 'zh' for Chinese, 'en' for everything else."""
    try:
        code, _ = locale.getlocale(locale.LC_CTYPE)
        if code and "Chinese" in code:
            return "zh"
    except Exception:
        pass
    return "en"


def get_l10n(lang: str = "auto") -> L10n:
    if lang == "auto":
        lang = detect_language()
    overrides = _ZH if lang == "zh" else {}
    return L10n(**overrides)