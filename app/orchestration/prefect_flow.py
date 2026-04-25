from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Callable

from prefect import flow, get_run_logger, task

from app.extract.client import GarminClient
from app.extract.run_recent import extract_date_range, extract_recent_range
from app.load.postgres_loader import PostgresLoader
from app.load.raw_writer import RawJsonWriter
from app.transform.run_sql import SqlRunner
from app.utils.config import PROJECT_ROOT, get_settings

STAGING_SQL_FILES = [
    PROJECT_ROOT / "sql" / "staging" / "001_stg_sleep.sql",
    PROJECT_ROOT / "sql" / "staging" / "002_stg_daily_health.sql",
    PROJECT_ROOT / "sql" / "staging" / "003_stg_activities.sql",
    PROJECT_ROOT / "sql" / "staging" / "004_stg_hrv.sql",
]
MART_SQL_FILES = [
    PROJECT_ROOT / "sql" / "marts" / "001_mart_sleep_correlates_daily.sql",
]
DEFAULT_QUALITY_CHECKS_DIR = PROJECT_ROOT / "sql" / "tests"


def _summarize_extract_results(results: dict[str, list[Path]]) -> dict[str, int]:
    return {dataset: len(paths) for dataset, paths in results.items()}


def _extract_range_summary(
    start_date: date,
    end_date: date,
    include_hrv: bool = True,
) -> dict[str, int]:
    settings = get_settings()
    results = extract_date_range(
        client=GarminClient(settings),
        writer=RawJsonWriter(settings),
        start_date=start_date,
        end_date=end_date,
        include_hrv=include_hrv,
    )
    return _summarize_extract_results(results)


def _extract_recent_summary(days: int, include_hrv: bool = True) -> dict[str, int]:
    settings = get_settings()
    results = extract_recent_range(
        client=GarminClient(settings),
        writer=RawJsonWriter(settings),
        days=days,
        include_hrv=include_hrv,
    )
    return _summarize_extract_results(results)


def _load_all_raw_summary() -> dict[str, int]:
    return PostgresLoader(get_settings()).load_all_raw_directories()


def _run_sql_files(sql_files: list[str | Path]) -> list[str]:
    runner = SqlRunner(get_settings())
    executed: list[str] = []
    for sql_file in sql_files:
        runner.run_file(sql_file)
        executed.append(str(Path(sql_file)))
    return executed


def _run_quality_checks(sql_dir: str | Path) -> list[str]:
    executed = SqlRunner(get_settings()).run_directory(sql_dir)
    return [str(path) for path in executed]


def _run_pipeline_sequence(
    extract_callable: Callable[[], dict[str, int]],
    load_callable: Callable[[], dict[str, int]],
    run_staging_callable: Callable[[], list[str]],
    run_mart_callable: Callable[[], list[str]],
    run_quality_checks_callable: Callable[[], list[str]],
) -> dict[str, Any]:
    return {
        "extract_counts": extract_callable(),
        "load_counts": load_callable(),
        "staging_sql_files": run_staging_callable(),
        "mart_sql_files": run_mart_callable(),
        "quality_check_files": run_quality_checks_callable(),
    }


@task(name="extract-range")
def extract_range_task(
    start_date: date,
    end_date: date,
    include_hrv: bool = True,
) -> dict[str, int]:
    return _extract_range_summary(start_date, end_date, include_hrv=include_hrv)


@task(name="extract-recent")
def extract_recent_task(days: int, include_hrv: bool = True) -> dict[str, int]:
    return _extract_recent_summary(days, include_hrv=include_hrv)


@task(name="load-raw")
def load_raw_task() -> dict[str, int]:
    return _load_all_raw_summary()


@task(name="run-sql-files")
def run_sql_files_task(sql_files: list[str]) -> list[str]:
    return _run_sql_files(sql_files)


@task(name="run-quality-checks")
def run_quality_checks_task(sql_dir: str) -> list[str]:
    return _run_quality_checks(sql_dir)


def run_pipeline_range_local(
    start_date: date,
    end_date: date,
    include_hrv: bool = True,
    quality_checks_dir: str | Path = DEFAULT_QUALITY_CHECKS_DIR,
) -> dict[str, Any]:
    return _run_pipeline_sequence(
        lambda: _extract_range_summary(start_date, end_date, include_hrv=include_hrv),
        _load_all_raw_summary,
        lambda: _run_sql_files(STAGING_SQL_FILES),
        lambda: _run_sql_files(MART_SQL_FILES),
        lambda: _run_quality_checks(quality_checks_dir),
    )


def run_pipeline_recent_local(
    days: int,
    include_hrv: bool = True,
    quality_checks_dir: str | Path = DEFAULT_QUALITY_CHECKS_DIR,
) -> dict[str, Any]:
    return _run_pipeline_sequence(
        lambda: _extract_recent_summary(days, include_hrv=include_hrv),
        _load_all_raw_summary,
        lambda: _run_sql_files(STAGING_SQL_FILES),
        lambda: _run_sql_files(MART_SQL_FILES),
        lambda: _run_quality_checks(quality_checks_dir),
    )


@flow(name="garmin-pipeline-range")
def run_pipeline_range_flow(
    start_date: date,
    end_date: date,
    include_hrv: bool = True,
    quality_checks_dir: str = str(DEFAULT_QUALITY_CHECKS_DIR),
) -> dict[str, Any]:
    logger = get_run_logger()
    logger.info(
        "Starting orchestrated Garmin pipeline for %s to %s. "
        "If Garmin authentication fails, disable your VPN and refresh GARMIN_MFA_CODE.",
        start_date,
        end_date,
    )
    return _run_pipeline_sequence(
        lambda: extract_range_task(start_date, end_date, include_hrv=include_hrv),
        load_raw_task,
        lambda: run_sql_files_task([str(path) for path in STAGING_SQL_FILES]),
        lambda: run_sql_files_task([str(path) for path in MART_SQL_FILES]),
        lambda: run_quality_checks_task(str(quality_checks_dir)),
    )


@flow(name="garmin-pipeline-recent")
def run_pipeline_recent_flow(
    days: int,
    include_hrv: bool = True,
    quality_checks_dir: str = str(DEFAULT_QUALITY_CHECKS_DIR),
) -> dict[str, Any]:
    logger = get_run_logger()
    logger.info(
        "Starting orchestrated recent Garmin pipeline for %s days. "
        "If Garmin authentication fails, disable your VPN and refresh GARMIN_MFA_CODE.",
        days,
    )
    return _run_pipeline_sequence(
        lambda: extract_recent_task(days, include_hrv=include_hrv),
        load_raw_task,
        lambda: run_sql_files_task([str(path) for path in STAGING_SQL_FILES]),
        lambda: run_sql_files_task([str(path) for path in MART_SQL_FILES]),
        lambda: run_quality_checks_task(str(quality_checks_dir)),
    )
