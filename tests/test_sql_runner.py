from __future__ import annotations

from pathlib import Path

import pytest

from app.transform.run_sql import SqlRunner
from app.utils.config import Settings


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        garmin_email="",
        garmin_password="",
        garmin_token_dir=tmp_path / "tokens",
        garmin_disable_env_proxy=True,
        garmin_mfa_enabled=True,
        garmin_mfa_code="",
        raw_data_dir=tmp_path / "raw",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="garmin_sleep",
        postgres_user="garmin",
        postgres_password="garmin",
        log_level="INFO",
    )


def test_run_directory_rejects_missing_path(tmp_path: Path) -> None:
    runner = SqlRunner(make_settings(tmp_path))

    with pytest.raises(FileNotFoundError, match="SQL directory does not exist"):
        runner.run_directory(tmp_path / "missing")


def test_run_directory_executes_sql_files_in_sorted_order(monkeypatch, tmp_path: Path) -> None:
    sql_dir = tmp_path / "sql" / "tests"
    sql_dir.mkdir(parents=True)
    (sql_dir / "002_second.sql").write_text("select 2;", encoding="utf-8")
    (sql_dir / "001_first.sql").write_text("select 1;", encoding="utf-8")

    executed: list[Path] = []
    runner = SqlRunner(make_settings(tmp_path))
    monkeypatch.setattr(runner, "run_file", lambda sql_file: executed.append(Path(sql_file)))

    sql_files = runner.run_directory(sql_dir)

    assert sql_files == [sql_dir / "001_first.sql", sql_dir / "002_second.sql"]
    assert executed == [sql_dir / "001_first.sql", sql_dir / "002_second.sql"]
