from __future__ import annotations

import argparse
import logging
from datetime import date

from app.extract.client import GarminClient
from app.extract.run_recent import extract_date_range, extract_recent_range
from app.load.postgres_loader import PostgresLoader
from app.load.raw_writer import RawJsonWriter
from app.transform.run_sql import SqlRunner
from app.utils.config import get_settings
from app.utils.logging import configure_logging

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
    return parser


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
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

    if args.command == "load-raw":
        loader = PostgresLoader(settings)
        if args.dataset == "all":
            results = loader.load_all_raw_directories()
            for dataset, count in results.items():
                LOGGER.info("%s files loaded: %s", dataset, count)
            return

        count = loader.load_dataset_directory(args.dataset)
        LOGGER.info("%s files loaded: %s", args.dataset, count)
        return

    if args.command == "run-sql":
        SqlRunner(settings).run_file(args.file)
        return

    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    main()
