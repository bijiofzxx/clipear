"""
cleaner.py — 文本清洗模块

将从网页/App 复制的原始文本清洗为适合朗读的纯净文本。
清洗分两层：
  1. 硬规则：结构噪音（图片占位、URL、Markdown、特殊字符等）
  2. 软规则：广告关键词行过滤（关键词列表来自 config.yaml）
"""

from __future__ import annotations

import html
import re


# ── 硬规则正则 ────────────────────────────────────────────────────────────────

# Markdown 图片 ![alt](url) 或 ![alt][ref]
_RE_MD_IMAGE = re.compile(r"!\[.*?\]\(.*?\)|!\[.*?\]\[.*?\]")

# Markdown 链接 [text](url) → 保留 text
_RE_MD_LINK = re.compile(r"\[([^\]]+)\]\([^\)]+\)")

# 裸 URL（http/https 开头，到空白/行尾结束）
_RE_BARE_URL = re.compile(r"https?://\S+")

# 中文图片占位符
_RE_CN_IMAGE = re.compile(r"\[图片\]|\[Image\]|\[img\]", re.IGNORECASE)

# Markdown 标题 # / ## / ###
_RE_MD_HEADING = re.compile(r"^#{1,6}\s+", re.MULTILINE)

# Markdown 粗体/斜体 **text** / *text* / __text__ / _text_
_RE_MD_BOLD_ITALIC = re.compile(r"(\*{1,3}|_{1,3})(.+?)\1")

# Markdown 行内代码 `code`
_RE_MD_CODE = re.compile(r"`+[^`]*`+")

# 全角空格 \u3000、零宽字符 \u200b \u200c \u200d \ufeff
_RE_INVISIBLE = re.compile(r"[\u3000\u200b\u200c\u200d\ufeff]")

# 连续超过 2 个换行 → 压缩为 2 个（保留段落感）
_RE_MULTI_BLANK = re.compile(r"\n{3,}")

# 行尾多余空白
_RE_TRAILING_SPACE = re.compile(r"[ \t]+$", re.MULTILINE)

# 纯符号行（只有标点/符号，无中英文实质内容）
_RE_SYMBOL_ONLY_LINE = re.compile(r"^[^\u4e00-\u9fa5a-zA-Z0-9]+$")


def clean(raw: str, ad_keywords: list[str]) -> str:
    """
    对原始复制文本执行完整清洗流程。

    Args:
        raw:          剪贴板原始文本
        ad_keywords:  广告关键词列表（来自 config.yaml）

    Returns:
        清洗后适合朗读的纯净文本
    """
    text = raw

    # 1. HTML 实体转义（&nbsp; &amp; 等）
    text = html.unescape(text)

    # 2. Markdown 图片 → 删除
    text = _RE_MD_IMAGE.sub("", text)

    # 3. 中文图片占位符 → 删除
    text = _RE_CN_IMAGE.sub("", text)

    # 4. Markdown 链接 [text](url) → 保留 text
    text = _RE_MD_LINK.sub(r"\1", text)

    # 5. 裸 URL → 删除
    text = _RE_BARE_URL.sub("", text)

    # 6. Markdown 标题符号 → 删除（保留标题文字）
    text = _RE_MD_HEADING.sub("", text)

    # 7. Markdown 粗体/斜体 → 保留内容文字
    text = _RE_MD_BOLD_ITALIC.sub(r"\2", text)

    # 8. Markdown 行内代码 → 删除
    text = _RE_MD_CODE.sub("", text)

    # 9. 不可见字符（全角空格、零宽字符）→ 删除
    text = _RE_INVISIBLE.sub("", text)

    # 10. 广告关键词行过滤（逐行匹配，整行删除）
    text = _filter_ad_lines(text, ad_keywords)

    # 11. 纯符号行 → 删除
    lines = text.splitlines()
    lines = [l for l in lines if not _RE_SYMBOL_ONLY_LINE.match(l.strip()) or not l.strip()]
    text = "\n".join(lines)

    # 12. 行尾多余空白
    text = _RE_TRAILING_SPACE.sub("", text)

    # 13. 连续空行压缩为最多 2 个换行
    text = _RE_MULTI_BLANK.sub("\n\n", text)

    return text.strip()


def _filter_ad_lines(text: str, keywords: list[str]) -> str:
    """
    逐行扫描：若该行包含任意广告关键词，则整行删除。
    关键词匹配忽略大小写。
    """
    if not keywords:
        return text

    # 预编译：用 | 合并所有关键词，一次扫描
    pattern = re.compile("|".join(re.escape(kw) for kw in keywords), re.IGNORECASE)

    cleaned_lines = [
        line for line in text.splitlines()
        if not pattern.search(line)
    ]
    return "\n".join(cleaned_lines)
