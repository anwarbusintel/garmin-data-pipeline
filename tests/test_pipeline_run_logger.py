from __future__ import annotations

from pathlib import Path
from uuid import UUID

from app.utils import pipeline_run_logger
from app.utils.config import Settings
from app.utils.pipeline_run_logger import PipelineRunLogger


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


def test_start_run_inserts_started_log_record(monkeypatch, tmp_path: Path) -> None:
    executed: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        def execute(self, query: str, params: tuple[object, ...]) -> None:
            executed.append((query, params))

        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            return None

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(pipeline_run_logger.psycopg, "connect", lambda dsn: FakeConnection())

    logger = PipelineRunLogger(make_settings(tmp_path))
    run_id = logger.start_run("load-raw", details={"dataset": "all"})

    assert isinstance(run_id, UUID)
    assert len(executed) == 1
    query, params = executed[0]
    assert "INSERT INTO pipeline_run_log" in query
    assert params[1] == "load-raw"
    assert params[2] == "started"
    assert isinstance(params[3], pipeline_run_logger.Jsonb)


def test_finish_success_updates_log_record(monkeypatch, tmp_path: Path) -> None:
    executed: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        def execute(self, query: str, params: tuple[object, ...]) -> None:
            executed.append((query, params))

        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            return None

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(pipeline_run_logger.psycopg, "connect", lambda dsn: FakeConnection())

    logger = PipelineRunLogger(make_settings(tmp_path))
    run_id = UUID("11111111-1111-1111-1111-111111111111")
    logger.finish_success(run_id, details={"files_loaded": {"sleep": 12}})

    assert len(executed) == 1
    query, params = executed[0]
    assert "UPDATE pipeline_run_log" in query
    assert params[0] == "success"
    assert isinstance(params[1], pipeline_run_logger.Jsonb)
    assert params[2] == run_id


def test_finish_failure_updates_log_record(monkeypatch, tmp_path: Path) -> None:
    executed: list[tuple[str, tuple[object, ...]]] = []

    class FakeCursor:
        def execute(self, query: str, params: tuple[object, ...]) -> None:
            executed.append((query, params))

        def __enter__(self) -> "FakeCursor":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    class FakeConnection:
        def cursor(self) -> FakeCursor:
            return FakeCursor()

        def commit(self) -> None:
            return None

        def __enter__(self) -> "FakeConnection":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setattr(pipeline_run_logger.psycopg, "connect", lambda dsn: FakeConnection())

    logger = PipelineRunLogger(make_settings(tmp_path))
    run_id = UUID("22222222-2222-2222-2222-222222222222")
    logger.finish_failure(
        run_id,
        error_message="boom",
        details={"dataset": "sleep"},
    )

    assert len(executed) == 1
    query, params = executed[0]
    assert "UPDATE pipeline_run_log" in query
    assert params[0] == "failed"
    assert params[1] == "boom"
    assert isinstance(params[2], pipeline_run_logger.Jsonb)
    assert params[3] == run_id


def test_start_run_swallows_database_errors(monkeypatch, tmp_path: Path, caplog) -> None:
    def fake_connect(dsn: str):
        raise RuntimeError("missing table")

    monkeypatch.setattr(pipeline_run_logger.psycopg, "connect", fake_connect)

    logger = PipelineRunLogger(make_settings(tmp_path))
    with caplog.at_level("WARNING"):
        run_id = logger.start_run("run-sql", details={"sql_file": "sql/marts/001.sql"})

    assert isinstance(run_id, UUID)
    assert "Unable to start pipeline run log for run-sql" in caplog.text
