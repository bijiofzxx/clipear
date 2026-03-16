"""
sys_notify.py — Windows 系统通知模块

使用 winotify 调用 Windows 10/11 原生 Toast 通知 API，
弹窗样式与系统通知中心完全一致。

安装依赖：pip install winotify

用法：
    from sys_notify import notify, NotifyLevel
    notify("标题", "内容")
    notify("标题", "内容", level=NotifyLevel.WARNING)
    notify("标题", "内容", level=NotifyLevel.ERROR, duration=5)
"""

from __future__ import annotations

from enum import Enum

from winotify import Notification, audio

# ── 配置 ──────────────────────────────────────────────────────────────────────
DEFAULT_DURATION_SECONDS = 3

APP_ID = "clipear"
# ─────────────────────────────────────────────────────────────────────────────


class NotifyLevel(str, Enum):
    INFO    = "info"
    WARNING = "warning"
    ERROR   = "error"


# 每个级别对应的标题前缀 emoji
_LEVEL_PREFIX: dict[NotifyLevel, str] = {
    NotifyLevel.INFO:    "✅",
    NotifyLevel.WARNING: "⚠️",
    NotifyLevel.ERROR:   "❌",
}


def notify(
    title: str,
    message: str,
    duration: int = DEFAULT_DURATION_SECONDS,
    level: NotifyLevel = NotifyLevel.INFO,
) -> None:
    """
    在 Windows 右下角显示 Toast 通知。

    Args:
        title:    通知标题（最多 63 字符）
        message:  通知正文（最多 255 字符）
        duration: 显示时长（秒）
                  <= 5 → Windows Toast "short"（约5秒后消失）
                  >  5 → Windows Toast "long" （约25秒后消失）
        level:    通知级别
                    NotifyLevel.INFO    → ✅ 普通信息
                    NotifyLevel.WARNING → ⚠️ 警告
                    NotifyLevel.ERROR   → ❌ 错误
    """
    prefix        = _LEVEL_PREFIX[level]
    display_title = f"{prefix} {title}"
    win_duration  = "long" if duration > 5 else "short"

    toast = Notification(
        app_id=APP_ID,
        title=display_title[:63],
        msg=message[:255],
        duration=win_duration
    )
    toast.build()
    toast.show()


