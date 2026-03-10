"""
hotkey.py — 全局热键监听模块

热键职责：
  Alt+Shift+S → 开始：触发新的朗读任务
  Alt+Shift+E → 结束：中断当前朗读任务
"""

from __future__ import annotations

import logging
import threading
from typing import Callable

import keyboard

logger = logging.getLogger("reader")

HOTKEY_START = "alt+shift+s"
HOTKEY_END   = "alt+shift+e"


class HotkeyManager:
    """
    管理双热键：
      - S 键永远触发新任务（有任务运行时给出提示，不误触）
      - E 键永远执行中断（无任务时静默忽略）
    """

    def __init__(self, on_trigger: Callable[[], None]) -> None:
        self._on_trigger = on_trigger
        self._stop_event: threading.Event | None = None
        self._lock = threading.Lock()

    def register(self) -> None:
        """注册全局热键，程序生命周期内只需调用一次。"""
        keyboard.add_hotkey(HOTKEY_START, self._handle_start, suppress=True)
        keyboard.add_hotkey(HOTKEY_END,   self._handle_end,   suppress=True)
        logger.info("热键已注册 — 开始：%s　结束：%s", HOTKEY_START.upper(), HOTKEY_END.upper())

    def set_stop_event(self, event: threading.Event) -> None:
        """任务开始时传入 stop_event，供 E 键中断使用。"""
        with self._lock:
            self._stop_event = event

    def clear_stop_event(self) -> None:
        """任务结束时清除 stop_event。"""
        with self._lock:
            self._stop_event = None

    # ── 内部回调 ──────────────────────────────────────────────────────────────

    def _handle_start(self) -> None:
        with self._lock:
            if self._stop_event is not None:
                logger.warning("任务正在运行，如需停止请按 %s", HOTKEY_END.upper())
            else:
                logger.info("检测到开始热键，启动新任务")
                self._on_trigger()

    def _handle_end(self) -> None:
        with self._lock:
            if self._stop_event is not None:
                logger.info("检测到结束热键，中断当前朗读任务")
                self._stop_event.set()
            else:
                logger.debug("检测到结束热键，当前无运行中的任务，忽略")
