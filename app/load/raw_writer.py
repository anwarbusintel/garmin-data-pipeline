from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.config import Settings


class RawJsonWriter:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def ensure_directories(self) -> None:
        for dataset in ("sleep", "daily_health", "activities", "hrv"):
            (self._settings.raw_data_dir / dataset).mkdir(parents=True, exist_ok=True)

    def write(self, dataset: str, record_key: str, payload: Any) -> Path:
        dataset_dir = self._settings.raw_data_dir / dataset
        dataset_dir.mkdir(parents=True, exist_ok=True)
        safe_key = record_key.replace(":", "-").replace("/", "-")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        file_path = dataset_dir / f"{safe_key}_{timestamp}.json"
        file_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return file_path
