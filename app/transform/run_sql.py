from __future__ import annotations

import logging
from pathlib import Path

import psycopg

from app.utils.config import Settings

LOGGER = logging.getLogger(__name__)


class SqlRunner:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run_file(self, sql_file: str | Path) -> None:
        path = Path(sql_file)
        sql_text = path.read_text(encoding="utf-8")
        with psycopg.connect(self._settings.postgres_dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql_text)
            conn.commit()

    def run_directory(self, sql_dir: str | Path) -> list[Path]:
        path = Path(sql_dir)
        if not path.exists():
            raise FileNotFoundError(f"SQL directory does not exist: {path}")
        if not path.is_dir():
            raise NotADirectoryError(f"SQL path is not a directory: {path}")

        sql_files = sorted(path.glob("*.sql"))
        for sql_file in sql_files:
            LOGGER.info("Running SQL file: %s", sql_file)
            self.run_file(sql_file)
        return sql_files
