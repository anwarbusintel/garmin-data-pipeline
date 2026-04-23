from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

from app.extract.client import GarminClient
from app.extract.extract_activities import extract_activities_range
from app.extract.extract_daily_health import extract_daily_health_range
from app.extract.extract_hrv import extract_hrv_range
from app.extract.extract_sleep import extract_sleep_range
from app.load.raw_writer import RawJsonWriter

LOGGER = logging.getLogger(__name__)


def extract_date_range(
    client: GarminClient,
    writer: RawJsonWriter,
    start_date: date,
    end_date: date,
    include_hrv: bool = True,
) -> dict[str, list[Path]]:
    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    writer.ensure_directories()
    LOGGER.info("Extracting Garmin data from %s to %s", start_date, end_date)

    results = {
        "sleep": extract_sleep_range(client, writer, start_date, end_date),
        "daily_health": extract_daily_health_range(client, writer, start_date, end_date),
        "activities": extract_activities_range(client, writer, start_date, end_date),
        "hrv": [],
    }

    if include_hrv:
        results["hrv"] = extract_hrv_range(client, writer, start_date, end_date)

    return results


def extract_recent_range(
    client: GarminClient,
    writer: RawJsonWriter,
    days: int,
    include_hrv: bool = True,
) -> dict[str, list[Path]]:
    if days < 1:
        raise ValueError("days must be at least 1")

    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)
    return extract_date_range(client, writer, start_date, end_date, include_hrv=include_hrv)
