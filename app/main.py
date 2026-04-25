from __future__ import annotations

import argparse
import logging
from datetime import date
from typing import Any, Callable

from app.extract.client import GarminClient
from app.extract.run_recent import extract_date_range, extract_recent_range
from app.load.postgres_loader import PostgresLoader
from app.load.raw_writer import RawJsonWriter
from app.orchestration.prefect_flow import (
    run_pipeline_range_flow,
    run_pipeline_recent_flow,
)
from app.transform.run_sql import SqlRunner
from app.utils.config import get_settings
from app.utils.logging import configure_logging
from app.utils.pipeline_run_logger import PipelineRunLogger

LOGGER = logging.getLogger(__name__)


def _parse_iso_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid date {value!r}. Expected YYYY-MM-DD."
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Garmin sleep pipeline utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("bootstrap", help="Create expected local raw-data directories")

    subparsers.add_parser("login-test", help="Authenticate against Garmin and validate access")

    extract_recent = subparsers.add_parser(
        "extract-recent",
        help="Extract a recent date range of Garmin data into raw JSON",
    )
    extract_recent.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of recent calendar days to pull, including today",
    )
    extract_recent.add_argument(
        "--skip-hrv",
        action="store_true",
        help="Skip HRV extraction if you only want core datasets",
    )

    extract_range = subparsers.add_parser(
        "extract-range",
        help="Extract a specific calendar date range of Garmin data into raw JSON",
    )
    extract_range.add_argument(
        "--start-date",
        type=_parse_iso_date,
        required=True,
        help="Inclusive start date in YYYY-MM-DD format",
    )
    extract_range.add_argument(
        "--end-date",
        type=_parse_iso_date,
        required=True,
        help="Inclusive end date in YYYY-MM-DD format",
    )
    extract_range.add_argument(
        "--skip-hrv",
        action="store_true",
        help="Skip HRV extraction if you only want core datasets",
    )

    run_pipeline_recent = subparsers.add_parser(
        "run-pipeline-recent",
        help="Run the end-to-end Prefect pipeline for a recent date window",
    )
    run_pipeline_recent.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of recent calendar days to pull, including today",
    )
    run_pipeline_recent.add_argument(
        "--skip-hrv",
        action="store_true",
        help="Skip HRV extraction if you only want core datasets",
    )

    run_pipeline_range = subparsers.add_parser(
        "run-pipeline-range",
        help="Run the end-to-end Prefect pipeline for an explicit date range",
    )
    run_pipeline_range.add_argument(
        "--start-date",
        type=_parse_iso_date,
        required=True,
        help="Inclusive start date in YYYY-MM-DD format",
    )
    run_pipeline_range.add_argument(
        "--end-date",
        type=_parse_iso_date,
        required=True,
        help="Inclusive end date in YYYY-MM-DD format",
    )
    run_pipeline_range.add_argument(
        "--skip-hrv",
        action="store_true",
        help="Skip HRV extraction if you only want core datasets",
    )

    load_raw = subparsers.add_parser(
        "load-raw",
        help="Load raw JSON files from local data directories into PostgreSQL",
    )
    load_raw.add_argument(
        "--dataset",
        choices=["sleep", "daily_health", "activities", "hrv", "all"],
        default="all",
        help="Which raw dataset directory to load",
    )

    run_sql = subparsers.add_parser("run-sql", help="Execute a SQL file against Postgres")
    run_sql.add_argument("--file", required=True, help="Path to the SQL file to execute")

    run_quality_checks = subparsers.add_parser(
        "run-quality-checks",
        help="Execute all SQL quality-check files in a directory against Postgres",
    )
    run_quality_checks.add_argument(
        "--dir",
        default="sql/tests",
        help="Directory containing SQL quality-check files to execute",
    )
    return parser


def _run_with_pipeline_log(
    pipeline_logger: PipelineRunLogger,
    pipeline_name: str,
    run_callable: Callable[[], Any],
    *,
    start_details: dict[str, Any] | None = None,
    success_details_builder: Callable[[Any], dict[str, Any]] | None = None,
) -> Any:
    run_id = pipeline_logger.start_run(pipeline_name, details=start_details)
    try:
        result = run_callable()
    except Exception as exc:
        pipeline_logger.finish_failure(run_id, error_message=str(exc))
        raise

    success_details = (
        success_details_builder(result)
        if success_details_builder is not None
        else {}
    )
    pipeline_logger.finish_success(run_id, details=success_details)
    return result


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    pipeline_logger = PipelineRunLogger(settings)
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "bootstrap":
        RawJsonWriter(settings).ensure_directories()
        return

    if args.command == "login-test":
        GarminClient(settings).login()
        LOGGER.info("Garmin login succeeded.")
        return

    if args.command == "extract-recent":
        results = extract_recent_range(
            client=GarminClient(settings),
            writer=RawJsonWriter(settings),
            days=args.days,
            include_hrv=not args.skip_hrv,
        )
        for dataset, paths in results.items():
            LOGGER.info("%s files written: %s", dataset, len(paths))
            for path in paths:
                LOGGER.info("  %s", path)
        return

    if args.command == "extract-range":
        results = extract_date_range(
            client=GarminClient(settings),
            writer=RawJsonWriter(settings),
            start_date=args.start_date,
            end_date=args.end_date,
            include_hrv=not args.skip_hrv,
        )
        for dataset, paths in results.items():
            LOGGER.info("%s files written: %s", dataset, len(paths))
            for path in paths:
                LOGGER.info("  %s", path)
        return

    if args.command == "run-pipeline-recent":
        summary = _run_with_pipeline_log(
            pipeline_logger,
            "run-pipeline-recent",
            lambda: run_pipeline_recent_flow(
                days=args.days,
                include_hrv=not args.skip_hrv,
            ),
            start_details={"days": args.days, "include_hrv": not args.skip_hrv},
            success_details_builder=lambda value: {
                "days": args.days,
                "include_hrv": not args.skip_hrv,
                "summary": value,
            },
        )
        LOGGER.info("Pipeline summary: %s", summary)
        return

    if args.command == "run-pipeline-range":
        summary = _run_with_pipeline_log(
            pipeline_logger,
            "run-pipeline-range",
            lambda: run_pipeline_range_flow(
                start_date=args.start_date,
                end_date=args.end_date,
                include_hrv=not args.skip_hrv,
            ),
            start_details={
                "start_date": args.start_date.isoformat(),
                "end_date": args.end_date.isoformat(),
                "include_hrv": not args.skip_hrv,
            },
            success_details_builder=lambda value: {
                "start_date": args.start_date.isoformat(),
                "end_date": args.end_date.isoformat(),
                "include_hrv": not args.skip_hrv,
                "summary": value,
            },
        )
        LOGGER.info("Pipeline summary: %s", summary)
        return

    if args.command == "load-raw":
        loader = PostgresLoader(settings)
        if args.dataset == "all":
            results = _run_with_pipeline_log(
                pipeline_logger,
                "load-raw",
                loader.load_all_raw_directories,
                start_details={"dataset": "all"},
                success_details_builder=lambda value: {
                    "dataset": "all",
                    "files_loaded": value,
                },
            )
            for dataset, count in results.items():
                LOGGER.info("%s files loaded: %s", dataset, count)
            return

        count = _run_with_pipeline_log(
            pipeline_logger,
            "load-raw",
            lambda: loader.load_dataset_directory(args.dataset),
            start_details={"dataset": args.dataset},
            success_details_builder=lambda value: {
                "dataset": args.dataset,
                "files_loaded": value,
            },
        )
        LOGGER.info("%s files loaded: %s", args.dataset, count)
        return

    if args.command == "run-sql":
        _run_with_pipeline_log(
            pipeline_logger,
            "run-sql",
            lambda: SqlRunner(settings).run_file(args.file),
            start_details={"sql_file": args.file},
            success_details_builder=lambda _: {"sql_file": args.file, "files_executed": 1},
        )
        return

    if args.command == "run-quality-checks":
        sql_files = _run_with_pipeline_log(
            pipeline_logger,
            "run-quality-checks",
            lambda: SqlRunner(settings).run_directory(args.dir),
            start_details={"sql_dir": args.dir},
            success_details_builder=lambda value: {
                "sql_dir": args.dir,
                "files_executed": len(value),
            },
        )
        LOGGER.info("Quality checks completed: %s files executed", len(sql_files))
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
