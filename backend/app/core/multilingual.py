"""
Multilingual Extraction Feature Flag & Scope Control.
Ensures non-English extraction pipelines remain isolated until dedicated
regression suites and validation passes are certified.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

CONFIG_PATH = Path(__file__).resolve().parent / "multilingual_config.json"

_DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "supported_languages": ["en"],
    "experimental_languages": ["zh-CN"],
    "require_dedicated_regression_suite": True,
}


def get_multilingual_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return data.get("multilingual_extraction", _DEFAULT_CONFIG)
        except Exception:
            return _DEFAULT_CONFIG
    return _DEFAULT_CONFIG


def is_multilingual_enabled(lang: str = "zh-CN") -> bool:
    """Checks whether extraction for a given language is currently active."""
    cfg = get_multilingual_config()
    if not cfg.get("enabled", False):
        return False
    supported = cfg.get("supported_languages", ["en"])
    experimental = cfg.get("experimental_languages", [])
    return lang in supported or lang in experimental
