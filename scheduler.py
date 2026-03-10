"""分段发送调度模块：逐段推送，动态 sleep，响应中断信号。"""

from __future__ import annotations

import logging
import threading
import time

from config import AppConfig
from notifier import push_segment, push_interrupted

logger = logging.getLogger("reader")

_POLL_INTERVAL = 0.2  # sleep 轮询粒度（秒），控制中断响应速度


def interruptible_sleep(seconds: float, stop_event: threading.Event) -> bool:
    """
    可中断的 sleep：每隔 _POLL_INTERVAL 检查 stop_event。

    Returns:
        True  → 正常睡完
        False → 被中断提前返回
    """
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if stop_event.is_set():
            return False
        time.sleep(min(_POLL_INTERVAL, deadline - time.monotonic()))
    return True


def send_segments(
    segments: list[str],
    title: str,
    config: AppConfig,
    stop_event: threading.Event,
) -> None:
    """
    按序推送所有段落：
    - 第1段立即发送，之后每段发送前先等待上一段的估算朗读时长
    - stop_event 置位时立即中断并推送提示
    """
    total = len(segments)
    bark_url = config.bark.url
    cps = config.reading.speed_cps
    buffer_sec = config.reading.buffer_seconds

    logger.info("开始推送：《%s》共 %d 段", title, total)

    prev_sleep: float = 0.0  # 上一段需要等待的秒数

    for idx, segment in enumerate(segments, start=1):
        # 从第2段起，先等待上一段的朗读时长
        if idx > 1 and prev_sleep > 0:
            logger.debug("等待上一段朗读完毕（%.1f 秒）…", prev_sleep)
            completed = interruptible_sleep(prev_sleep, stop_event)
            if not completed:
                logger.info("朗读任务被中断，已发送 %d/%d 段", idx - 1, total)
                push_interrupted(bark_url)
                return

        if stop_event.is_set():
            logger.info("朗读任务被中断（发送前检查），已发送 %d/%d 段", idx - 1, total)
            push_interrupted(bark_url)
            return

        success = push_segment(bark_url, title, segment, idx, total)
        if not success:
            logger.error("第 %d 段推送失败，中止任务", idx)
            return

        # 计算本段朗读估算时长，供下一轮 sleep 使用
        prev_sleep = len(segment) / cps + buffer_sec
        logger.debug("第 %d/%d 段已发送，估算朗读时长 %.1f 秒", idx, total, prev_sleep)

    logger.info("《%s》全部 %d 段推送完成", title, total)
