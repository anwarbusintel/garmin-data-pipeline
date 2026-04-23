from __future__ import annotations

from pathlib import Path

import psycopg

from app.utils.config import Settings


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
