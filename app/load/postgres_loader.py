from __future__ import annotations

import json
from datetime import date
import logging
from pathlib import Path
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from app.utils.config import Settings

RAW_TABLES = {"raw_sleep", "raw_daily_health", "raw_activities", "raw_hrv"}
DATASET_TABLE_MAP = {
    "sleep": "raw_sleep",
    "daily_health": "raw_daily_health",
    "activities": "raw_activities",
    "hrv": "raw_hrv",
}
LOGGER = logging.getLogger(__name__)


class PostgresLoader:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def load_raw_record(
        self,
        table_name: str,
        payload: Any,
        source_file: str,
        calendar_date: date | None = None,
    ) -> None:
        if table_name not in RAW_TABLES:
            raise ValueError(f"Unsupported raw table: {table_name}")

        query = (
            f"INSERT INTO {table_name} (calendar_date, source_file, payload) "
            "VALUES (%s, %s, %s) "
            "ON CONFLICT (source_file) DO UPDATE SET "
            "calendar_date = EXCLUDED.calendar_date, "
            "payload = EXCLUDED.payload, "
            "fetched_at = NOW()"
        )
        with psycopg.connect(self._settings.postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (calendar_date, source_file, Jsonb(payload)))
            conn.commit()

    def load_raw_file(
        self,
        table_name: str,
        file_path: str | Path,
        calendar_date: date | None = None,
    ) -> None:
        path = Path(file_path)
        payload = json.loads(path.read_text(encoding="utf-8"))
        self.load_raw_record(
            table_name=table_name,
            payload=payload,
            source_file=path.name,
            calendar_date=calendar_date,
        )

    def load_dataset_directory(self, dataset: str) -> int:
        table_name = DATASET_TABLE_MAP.get(dataset)
        if table_name is None:
            raise ValueError(f"Unsupported dataset: {dataset}")

        dataset_dir = self._settings.raw_data_dir / dataset
        if not dataset_dir.exists():
            raise FileNotFoundError(f"Dataset directory does not exist: {dataset_dir}")

        file_paths = sorted(dataset_dir.glob("*.json"))
        for path in file_paths:
            self.load_raw_file(table_name=table_name, file_path=path)
        LOGGER.info("Loaded %s files into %s", len(file_paths), table_name)
        return len(file_paths)

    def load_all_raw_directories(self) -> dict[str, int]:
        return {
            dataset: self.load_dataset_directory(dataset)
            for dataset in DATASET_TABLE_MAP
        }
