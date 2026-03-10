"""Bark 推送模块：封装 HTTP 请求，含重试逻辑。"""

from __future__ import annotations

import logging
import time

import requests

logger = logging.getLogger("reader")

_MAX_RETRIES = 3
_RETRY_DELAY = 2  # 秒


def push(
    bark_url: str,
    title: str,
    body: str,
    *,
    retries: int = _MAX_RETRIES,
) -> bool:
    """
    发送 Bark 推送通知。

    Args:
        bark_url: Bark 设备推送地址，如 https://api.day.app/token
        title:    通知标题
        body:     通知正文
        retries:  失败重试次数

    Returns:
        True 表示推送成功，False 表示全部重试失败。
    """
    url = bark_url.rstrip("/")
    payload = {"title": title, "body": body, "sound": "minuet"}

    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(url, json=payload, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") == 200:
                logger.debug("Bark 推送成功：%s", title)
                return True
            logger.warning("Bark 返回非200：%s", data)
        except requests.RequestException as exc:
            logger.warning("Bark 推送失败（第%d次）：%s", attempt, exc)
            if attempt < retries:
                time.sleep(_RETRY_DELAY)

    logger.error("Bark 推送彻底失败，已重试 %d 次：%s", retries, title)
    return False


# ── 语义化快捷函数 ────────────────────────────────────────────────────────────

def push_invalid_clipboard(bark_url: str) -> bool:
    return push(bark_url, "⚠️ AIRPODS_监控", "剪贴板非网址无法获取并朗读")


def push_fetch_error(bark_url: str, reason: str, url: str) -> bool:
    body = f"错误原因：{reason}\nURL：{url}"
    return push(bark_url, "❌ 获取文章失败", body)


def push_wechat_blocked(bark_url: str) -> bool:
    return push(bark_url, "⚠️ 微信公众号", "公众号文章无法自动获取，请手动复制文字后使用")


def push_segment(bark_url: str, title: str, body: str, index: int, total: int) -> bool:
    segment_title = f"📖 {title} [{index}/{total}]"
    return push(bark_url, segment_title, body)


def push_interrupted(bark_url: str) -> bool:
    return push(bark_url, "⏹ 已中断朗读", "当前文章朗读任务已停止")
