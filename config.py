"""配置加载模块：读取并校验 config.yaml"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


CONFIG_PATH = Path(__file__).parent / "config.yaml"


@dataclass
class BarkConfig:
    url: str


@dataclass
class LoggingConfig:
    file: str


@dataclass
class SplitConfig:
    chars_per_segment: int


@dataclass
class ReadingConfig:
    speed_cps: float
    buffer_seconds: float


@dataclass
class CleanerConfig:
    ad_keywords: list[str] = field(default_factory=list)


@dataclass
class AppConfig:
    bark: BarkConfig
    logging: LoggingConfig
    split: SplitConfig
    reading: ReadingConfig
    cleaner: CleanerConfig


def load_config(path: Path = CONFIG_PATH) -> AppConfig:
    """从 YAML 文件加载配置，缺失必填项时抛出 ValueError。"""
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    bark_url = raw.get("bark", {}).get("url", "")
    if not bark_url or "your_token" in bark_url:
        raise ValueError("请在 config.yaml 中设置有效的 bark.url")

    return AppConfig(
        bark=BarkConfig(url=bark_url),
        logging=LoggingConfig(
            file=raw.get("logging", {}).get("file", "logs/reader.log")
        ),
        split=SplitConfig(
            chars_per_segment=raw.get("split", {}).get("chars_per_segment", 300)
        ),
        reading=ReadingConfig(
            speed_cps=raw.get("reading", {}).get("speed_cps", 4.5),
            buffer_seconds=raw.get("reading", {}).get("buffer_seconds", 2.0),
        ),
        cleaner=CleanerConfig(
            ad_keywords=raw.get("cleaner", {}).get("ad_keywords", [])
        ),
    )
