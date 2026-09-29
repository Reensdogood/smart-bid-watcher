from __future__ import annotations

import json
import os
from pathlib import Path

from .models import AppConfig


APP_DIR_NAME = "SmartBidWatcher"


def app_data_dir() -> Path:
    root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    path = root / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


class ConfigStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or app_data_dir() / "config.json"

    def load(self) -> AppConfig:
        if not self.path.exists():
            return AppConfig()
        try:
            return AppConfig.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return AppConfig()

    def save(self, config: AppConfig) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)
