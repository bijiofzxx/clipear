"""
hotkey.py — 全局热键监听模块

使用 pynput + Win32 虚拟键码（vk）匹配，彻底绕开大小写/输入法转换问题：
  - 字符匹配依赖 pynput 的字符解析，受输入法/Shift 状态影响
  - vk 匹配直接对应物理按键，无论大小写、输入法状态都稳定命中

━━━ 用户配置区（只需改这里）━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
填写三个按键名，格式参考：
  修饰键：'alt'  'shift'  'ctrl'
  字母键：'s'  'e'  'a' ...（填小写即可，实际用 vk 匹配，大小写无关）
"""

from __future__ import annotations

import logging
import queue
import threading

from pynput import keyboard as kb

logger = logging.getLogger("reader")

# ── 用户配置：组合键定义 ───────────────────────────────────────────────────────
# 修改这三行即可更换热键，字母填小写，修饰键填 'alt'/'shift'/'ctrl'
MODIFIER_KEYS = ['ctrl', 'shift']   # 需要同时按住的修饰键
START_KEY     = 's'                # 开始朗读的触发键
END_KEY       = 'e'                # 中断朗读的触发键
# ─────────────────────────────────────────────────────────────────────────────

# 信号常量（内部使用）
SIG_START = "start"

# ── 将配置转换为 pynput 对象（启动时执行一次）────────────────────────────────

def _parse_modifier(name: str) -> kb.Key:
    """将修饰键名称转换为 pynput Key 对象。"""
    mapping = {
        'alt':   kb.Key.alt,
        'shift': kb.Key.shift,
        'ctrl':  kb.Key.ctrl,
    }
    key = mapping.get(name.lower())
    if key is None:
        raise ValueError(f"不支持的修饰键：{name!r}，可选：{list(mapping)}")
    return key


def _char_to_vk(char: str) -> int:
    """
    将字母字符转换为 Windows 虚拟键码（vk）。
    vk 与大小写无关，Alt+Shift 按下时仍能稳定匹配。
    """
    import ctypes
    user32 = ctypes.windll.user32
    user32.VkKeyScanW.argtypes = [ctypes.c_wchar]
    user32.VkKeyScanW.restype  = ctypes.c_short
    vk = user32.VkKeyScanW(char.lower())
    if vk == -1:
        raise ValueError(f"无法解析按键：{char!r}")
    return vk & 0xFF   # 低字节为 vk，高字节为修饰键状态，只取低字节


# 启动时解析配置
_REQUIRED_MODS: set[kb.Key] = {_parse_modifier(m) for m in MODIFIER_KEYS}
_START_VK: int = _char_to_vk(START_KEY)
_END_VK:   int = _char_to_vk(END_KEY)

# 修饰键的所有变体（left/right）→ 归一化为通用键
_MOD_VARIANTS: dict[kb.Key, kb.Key] = {
    kb.Key.alt_l:   kb.Key.alt,
    kb.Key.alt_r:   kb.Key.alt,
    kb.Key.shift_l: kb.Key.shift,
    kb.Key.shift_r: kb.Key.shift,
    kb.Key.ctrl_l:  kb.Key.ctrl,
    kb.Key.ctrl_r:  kb.Key.ctrl,
}


class HotkeyManager:
    """
    基于 pynput 的全局热键管理器。

    匹配逻辑：
      - 修饰键通过归一化后的 Key 枚举追踪
      - 功能键通过 vk（虚拟键码）匹配，与大小写/输入法状态完全无关
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop_event: threading.Event | None = None
        self._lock = threading.Lock()
        self._active_mods: set[kb.Key] = set()   # 当前按下的修饰键（归一化后）
        self._listener: kb.Listener | None = None

    def register(self) -> None:
        """启动 pynput 监听器，程序生命周期内只需调用一次。"""
        self._listener = kb.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.daemon = True
        self._listener.start()

        mod_str   = '+'.join(m.upper() for m in MODIFIER_KEYS)
        start_str = f"{mod_str}+{START_KEY.upper()}"
        end_str   = f"{mod_str}+{END_KEY.upper()}"
        logger.info("热键已注册 — 开始：%s　结束：%s", start_str, end_str)

    def set_stop_event(self, event: threading.Event) -> None:
        """任务开始时传入 stop_event，供结束键中断使用。"""
        with self._lock:
            self._stop_event = event

    def clear_stop_event(self) -> None:
        """任务结束时清除 stop_event。"""
        with self._lock:
            self._stop_event = None

    def run_loop(self, on_start: callable, stop_flag: threading.Event) -> None:
        """
        主线程信号消费循环，阻塞运行直到 stop_flag 被置位。

        Args:
            on_start:  收到 SIG_START 时执行的回调
            stop_flag: 程序退出信号（Ctrl+C 时置位）
        """
        logger.info("信号消费循环启动，等待热键…")
        while not stop_flag.is_set():
            try:
                sig = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if sig == SIG_START:
                on_start()

        if self._listener:
            self._listener.stop()

    # ── pynput 回调 ───────────────────────────────────────────────────────────

    def _on_press(self, key: kb.Key | kb.KeyCode) -> None:
        # 1. 修饰键：归一化后加入追踪集合
        normalized = _MOD_VARIANTS.get(key)
        if normalized is not None:
            self._active_mods.add(normalized)
            return

        # 2. 修饰键未全部按下，忽略
        if not _REQUIRED_MODS.issubset(self._active_mods):
            return

        # 3. 用 vk 匹配功能键，与大小写/输入法无关
        vk = getattr(key, 'vk', None)
        if vk is None:
            return

        if vk == _START_VK:
            self._queue.put_nowait(SIG_START)
            logger.debug("检测到开始热键，投递信号")

        elif vk == _END_VK:
            with self._lock:
                if self._stop_event is not None:
                    self._stop_event.set()
                    logger.info("检测到结束热键，中断当前朗读任务")

    def _on_release(self, key: kb.Key | kb.KeyCode) -> None:
        # 修饰键释放时从追踪集合移除
        normalized = _MOD_VARIANTS.get(key)
        if normalized is not None:
            self._active_mods.discard(normalized)