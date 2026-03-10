"""clipboard.py — 剪贴板读取模块（简化版，不再做 URL 校验）"""

from __future__ import annotations

import pyperclip


def get_clipboard_text() -> str:
    """读取剪贴板文本，返回去除首尾空白后的字符串。"""
    return pyperclip.paste().strip()


def is_empty(text: str) -> bool:
    """判断文本是否为空或纯空白。"""
    return not bool(text)
