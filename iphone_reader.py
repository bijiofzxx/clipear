"""
iphone_reader.py — 主入口

用法：
  python iphone_reader.py

操作说明：
  Ctrl+Shift+S  先复制文章文字，再按此键 → 清洗分段推送到 iPhone 朗读
  Ctrl+Shift+E  中断当前朗读任务
  Ctrl+C       退出程序
"""

from __future__ import annotations

import logging
import sys
import threading
import time

from config import load_config, AppConfig
from logger import setup_logger
from hotkey import HotkeyManager
from clipboard import get_clipboard_text, is_empty
from cleaner import clean
from splitter import split_text
from scheduler import send_segments
from notifier import Notifier


def run_task(config: AppConfig, hotkey_mgr: HotkeyManager) -> None:
    """
    单次任务主流程：
    1. 读取剪贴板
    2. 判空
    3. 清洗文本
    4. 分段推送
    """
    logger = logging.getLogger("reader")

    # ── 1. 读取剪贴板 ────────────────────────────────────────────────────────
    text = get_clipboard_text()

    if is_empty(text):
        logger.warning("剪贴板为空，推送提示")
        Notifier(config.email, logger=logger).send(f"{config.name}告警", "剪贴板为空，请先复制文章内容")
        return

    logger.info("读取剪贴板成功，原始字数：%d", len(text))

    # ── 2. 清洗文本 ──────────────────────────────────────────────────────────
    cleaned = clean(text, config.cleaner.ad_keywords)
    logger.info("清洗完成，清洗后字数：%d（减少 %d 字）", len(cleaned), len(text) - len(cleaned))

    if is_empty(cleaned):
        logger.warning("清洗后文本为空")
        Notifier(config.email, logger=logger).send(f"{config.name}告警", "清洗后内容为空，请检查复制的文本")
        return

    # ── 3. 分段 ──────────────────────────────────────────────────────────────
    segments = split_text(cleaned, config.split.chars_per_segment)
    logger.info("分段完成：共 %d 段", len(segments))

    # ── 4. 分段推送（可中断）────────────────────────────────────────────────
    stop_event = threading.Event()
    hotkey_mgr.set_stop_event(stop_event)
    try:
        send_segments(segments, title="文章朗读", config=config, stop_event=stop_event)
    finally:
        hotkey_mgr.clear_stop_event()


def main() -> None:
    # ── 加载配置 ─────────────────────────────────────────────────────────────
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as exc:
        print(f"[错误] 配置加载失败：{exc}", file=sys.stderr)
        sys.exit(1)

    logger = setup_logger(config.logging.file)
    logger.info(f"iphone_reader 启动")
    logger.info("操作说明：复制文章文字后按 CTRL+SHIFT+S 开始朗读，按 CTRL+SHIFT+E 停止")

    # ── 热键注册 ─────────────────────────────────────────────────────────────
    _task_lock = threading.Lock()

    def on_trigger() -> None:
        """热键回调：在独立线程中运行任务，_task_lock 防止重复触发。"""
        if not _task_lock.acquire(blocking=False):
            logger.warning("任务正在运行，本次触发被忽略")
            return

        def _run() -> None:
            try:
                run_task(config, hotkey_mgr)
            except Exception as exc:
                logger.exception("任务异常：%s", exc)
            finally:
                _task_lock.release()

        threading.Thread(target=_run, daemon=True).start()

    hotkey_mgr = HotkeyManager(on_trigger=on_trigger)
    hotkey_mgr.register()

    # ── 主循环 ───────────────────────────────────────────────────────────────
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("程序已退出（Ctrl+C）")


if __name__ == "__main__":
    main()
