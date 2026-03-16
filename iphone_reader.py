"""
iphone_reader.py — 主入口

用法：
  python iphone_reader.py

操作说明：
  CTRL+SHIFT+S  先复制文章文字，再按此键 → 清洗分段推送到 iPhone 朗读
  CTRL+SHIFT+E  中断当前朗读任务
  Ctrl+C       退出程序

架构说明：
  钩子回调 → Queue 投递信号（微秒级返回，不会被 Windows 超时卸载）
  主线程   → 消费 Queue，驱动任务
  任务线程 → 独立线程执行清洗/推送，不阻塞主线程
"""

from __future__ import annotations

import logging
import signal
import sys
import threading

from config import load_config, AppConfig
from logger import setup_logger
from hotkey import HotkeyManager
from clipboard import get_clipboard_text, is_empty
from cleaner import clean
from splitter import split_text
from scheduler import send_segments

from sys_notify import notify, NotifyLevel


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
        notify("AIRPODS_监控", "剪贴板为空，请先复制文章内容", level=NotifyLevel.ERROR)
        return

    logger.info("读取剪贴板成功，原始字数：%d", len(text))

    # ── 2. 清洗文本 ──────────────────────────────────────────────────────────
    cleaned = clean(text, config.cleaner.ad_keywords)
    logger.info("清洗完成，清洗后字数：%d（减少 %d 字）", len(cleaned), len(text) - len(cleaned))

    if is_empty(cleaned):
        logger.warning("清洗后文本为空")
        notify("AIRPODS_监控", "清洗后内容为空，请检查复制的文本", level=NotifyLevel.ERROR)
        return

    # ── 3. 分段 ──────────────────────────────────────────────────────────────
    segments = split_text(cleaned, config.split.chars_per_segment)
    logger.info("分段完成：共 %d 段", len(segments))

    # ── 4. 分段推送（可中断）────────────────────────────────────────────────
    stop_event = threading.Event()
    hotkey_mgr.set_stop_event(stop_event)
    total_len = len(cleaned)
    total_minute = total_len // (config.reading.speed_cps * 60)
    total_split = len(segments)
    title = f"{config.name},{total_len}字,大约需要:{total_minute}分钟,共{total_split}段"
    try:
        send_segments(segments, title=title, config=config, stop_event=stop_event)
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
    logger.info("clipear 启动")
    logger.info("操作说明：复制文章文字后按 CTRL+SHIFT+S 开始朗读，按 CTRL+SHIFT+E 停止")

    # ── 程序退出信号 ─────────────────────────────────────────────────────────
    stop_flag = threading.Event()

    def _on_sigint(*_) -> None:
        logger.info("收到退出信号，正在关闭…")
        stop_flag.set()

    signal.signal(signal.SIGINT, _on_sigint)

    # ── 任务防重入：用 Event 标记是否有任务正在运行 ──────────────────────────
    _task_running = threading.Event()

    def on_start() -> None:
        """
        主线程消费 Queue 信号后调用此函数。
        任务在独立线程运行，on_start 本身立即返回，不阻塞主线程的信号消费循环。
        """
        # 防重入：set() 在 _run 线程里执行，此处只读，无竞态风险
        if _task_running.is_set():
            logger.warning("任务正在运行，本次触发被忽略（按 CTRL+SHIFT+E 可中断）")
            return

        def _run() -> None:
            _task_running.set()
            try:
                run_task(config, hotkey_mgr)
            except Exception as exc:
                logger.exception("任务异常：%s", exc)
            finally:
                _task_running.clear()

        threading.Thread(target=_run, name="task-runner", daemon=True).start()

    # ── 注册热键，启动主循环 ─────────────────────────────────────────────────
    hotkey_mgr = HotkeyManager()
    hotkey_mgr.register()

    # run_loop 在主线程阻塞运行，Ctrl+C 后 stop_flag 置位退出
    hotkey_mgr.run_loop(on_start=on_start, stop_flag=stop_flag)

    logger.info("clipear 已退出")


if __name__ == "__main__":
    main()