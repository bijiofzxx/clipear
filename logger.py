"""日志模块：屏幕 + 文件双输出，文件按天滚动。"""

from __future__ import annotations

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path


def setup_logger(log_file: str, name: str = "reader") -> logging.Logger:
    """
    初始化并返回 logger。
    - 屏幕：INFO 级别，带颜色前缀
    - 文件：DEBUG 级别，按天滚动，保留 30 天
    """
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger  # 避免重复注册

    fmt = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 屏幕 handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(fmt)

    # 文件 handler：按天滚动，midnight 切割，保留 30 份
    file_handler = TimedRotatingFileHandler(
        filename=str(log_path),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    file_handler.suffix = "%Y-%m-%d"

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger
