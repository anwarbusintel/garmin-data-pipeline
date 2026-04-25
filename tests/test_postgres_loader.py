from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.load import postgres_loader
from app.load.postgres_loader import PostgresLoader
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


def test_load_raw_record_rejects_unknown_table(tmp_path: Path) -> None:
    loader = PostgresLoader(make_settings(tmp_path))

    with pytest.raises(ValueError, match="Unsupported raw table"):
        loader.load_raw_record("raw_unknown", payload={}, source_file="sample.json")


def test_load_raw_record_executes_upsert_query(monkeypatch, tmp_path: Path) -> None:
    executed: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        def execute(self, query: str, params: tuple[object, ...]) -> None:
            executed.append((query, params))

        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class FakeConnection:
        def __init__(self) -> None:
            self.committed = False

        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            self.committed = True

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    fake_connection = FakeConnection()
    monkeypatch.setattr(postgres_loader.psycopg, "connect", lambda dsn: fake_connection)

    loader = PostgresLoader(make_settings(tmp_path))
    loader.load_raw_record(
        table_name="raw_sleep",
        payload={"sleep_score": 90},
        source_file="sleep_20260424.json",
        calendar_date=date(2026, 4, 24),
    )

    assert fake_connection.committed is True
    assert len(executed) == 1
    query, params = executed[0]
    assert "INSERT INTO raw_sleep" in query
    assert "ON CONFLICT (source_file) DO UPDATE" in query
    assert params[0] == date(2026, 4, 24)
    assert params[1] == "sleep_20260424.json"
    assert isinstance(params[2], postgres_loader.Jsonb)


def test_load_dataset_directory_raises_for_missing_directory(tmp_path: Path) -> None:
    loader = PostgresLoader(make_settings(tmp_path))

    with pytest.raises(FileNotFoundError, match="Dataset directory does not exist"):
        loader.load_dataset_directory("sleep")


def test_load_dataset_directory_loads_files_in_sorted_order(monkeypatch, tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    dataset_dir = settings.raw_data_dir / "sleep"
    dataset_dir.mkdir(parents=True)
    (dataset_dir / "b.json").write_text("{}", encoding="utf-8")
    (dataset_dir / "a.json").write_text("{}", encoding="utf-8")

    loaded_files: list[str] = []
    loader = PostgresLoader(settings)

    def fake_load_raw_file(table_name: str, file_path: str | Path, calendar_date=None) -> None:
        loaded_files.append(f"{table_name}:{Path(file_path).name}")

    monkeypatch.setattr(loader, "load_raw_file", fake_load_raw_file)

    count = loader.load_dataset_directory("sleep")

    assert count == 2
    assert loaded_files == ["raw_sleep:a.json", "raw_sleep:b.json"]
