from __future__ import annotations

from datetime import date
from pathlib import Path

from app.orchestration import prefect_flow


def test_run_pipeline_sequence_executes_steps_in_order() -> None:
    call_order: list[str] = []

    def extract_callable() -> dict[str, int]:
        call_order.append("extract")
        return {"sleep": 3}

    def load_callable() -> dict[str, int]:
        call_order.append("load")
        return {"sleep": 3, "daily_health": 3, "activities": 1, "hrv": 2}

    def run_staging_callable() -> list[str]:
        call_order.append("staging")
        return ["sql/staging/001_stg_sleep.sql"]

    def run_mart_callable() -> list[str]:
        call_order.append("mart")
        return ["sql/marts/001_mart_sleep_correlates_daily.sql"]

    def run_quality_checks_callable() -> list[str]:
        call_order.append("quality")
        return ["sql/tests/001_mart_sleep_core_assertions.sql"]

    result = prefect_flow._run_pipeline_sequence(
        extract_callable,
        load_callable,
        run_staging_callable,
        run_mart_callable,
        run_quality_checks_callable,
    )

    assert call_order == ["extract", "load", "staging", "mart", "quality"]
    assert result["extract_counts"] == {"sleep": 3}
    assert result["load_counts"]["activities"] == 1


def test_run_pipeline_range_local_uses_expected_arguments(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []

    def fake_extract_range_summary(start_date, end_date, include_hrv=True):
        calls.append(("extract", (start_date, end_date, include_hrv)))
        return {"sleep": 2, "daily_health": 2, "activities": 1, "hrv": 0}

    def fake_load_all_raw_summary():
        calls.append(("load", None))
        return {"sleep": 2, "daily_health": 2, "activities": 1, "hrv": 0}

    def fake_run_sql_files(sql_files):
        normalized = [Path(sql_file).name for sql_file in sql_files]
        calls.append(("sql", normalized))
        return [str(Path(sql_file)) for sql_file in sql_files]

    def fake_run_quality_checks(sql_dir):
        calls.append(("quality", Path(sql_dir).name))
        return [str(Path(sql_dir) / "001_mart_sleep_core_assertions.sql")]

    monkeypatch.setattr(prefect_flow, "_extract_range_summary", fake_extract_range_summary)
    monkeypatch.setattr(prefect_flow, "_load_all_raw_summary", fake_load_all_raw_summary)
    monkeypatch.setattr(prefect_flow, "_run_sql_files", fake_run_sql_files)
    monkeypatch.setattr(prefect_flow, "_run_quality_checks", fake_run_quality_checks)

    result = prefect_flow.run_pipeline_range_local(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 3),
        include_hrv=False,
        quality_checks_dir=tmp_path / "quality_checks",
    )

    assert calls == [
        ("extract", (date(2026, 4, 1), date(2026, 4, 3), False)),
        ("load", None),
        ("sql", ["001_stg_sleep.sql", "002_stg_daily_health.sql", "003_stg_activities.sql", "004_stg_hrv.sql"]),
        ("sql", ["001_mart_sleep_correlates_daily.sql"]),
        ("quality", "quality_checks"),
    ]
    assert result["extract_counts"]["sleep"] == 2
    assert result["quality_check_files"] == [
        str((tmp_path / "quality_checks") / "001_mart_sleep_core_assertions.sql")
    ]


def test_run_pipeline_recent_local_uses_days_argument(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_extract_recent_summary(days, include_hrv=True):
        captured["days"] = days
        captured["include_hrv"] = include_hrv
        return {"sleep": 5, "daily_health": 5, "activities": 1, "hrv": 5}

    monkeypatch.setattr(prefect_flow, "_extract_recent_summary", fake_extract_recent_summary)
    monkeypatch.setattr(prefect_flow, "_load_all_raw_summary", lambda: {"sleep": 5})
    monkeypatch.setattr(prefect_flow, "_run_sql_files", lambda sql_files: [str(Path(sql_file)) for sql_file in sql_files])
    monkeypatch.setattr(prefect_flow, "_run_quality_checks", lambda sql_dir: [str(Path(tmp_path) / "checks.sql")])

    result = prefect_flow.run_pipeline_recent_local(
        days=5,
        include_hrv=True,
        quality_checks_dir=tmp_path / "sql_tests",
    )

    assert captured == {"days": 5, "include_hrv": True}
    assert result["extract_counts"]["sleep"] == 5
