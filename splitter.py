"""文本分段模块：按句号边界切割，每段不超过 chars_per_segment 字。"""

from __future__ import annotations

import re

# 中英文句子结束标点
_SENTENCE_END = re.compile(r"([。！？!?…]+)")


def split_text(text: str, chars_per_segment: int) -> list[str]:
    """
    将长文本切割为若干段，规则：
    1. 先按句子边界拆分
    2. 累积句子，超过 chars_per_segment 时输出一段
    3. 单句超长时强制按字数截断
    """
    sentences = _split_sentences(text)
    segments: list[str] = []
    buffer = ""

    for sentence in sentences:
        # 单句本身超长 → 强制截断后入队
        if len(sentence) > chars_per_segment:
            if buffer:
                segments.append(buffer.strip())
                buffer = ""
            for chunk in _force_split(sentence, chars_per_segment):
                segments.append(chunk.strip())
            continue

        if len(buffer) + len(sentence) > chars_per_segment:
            if buffer:
                segments.append(buffer.strip())
            buffer = sentence
        else:
            buffer += sentence

    if buffer.strip():
        segments.append(buffer.strip())

    return [s for s in segments if s]


def _split_sentences(text: str) -> list[str]:
    """按标点将文本拆为句子列表，保留标点附在句尾。"""
    parts = _SENTENCE_END.split(text)
    sentences: list[str] = []
    i = 0
    while i < len(parts):
        part = parts[i]
        if i + 1 < len(parts) and _SENTENCE_END.fullmatch(parts[i + 1]):
            sentences.append(part + parts[i + 1])
            i += 2
        else:
            if part:
                sentences.append(part)
            i += 1
    return sentences


def _force_split(text: str, size: int) -> list[str]:
    """强制按固定字数截断（兜底逻辑）。"""
    return [text[i : i + size] for i in range(0, len(text), size)]
