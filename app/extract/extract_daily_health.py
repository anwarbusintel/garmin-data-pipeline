from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from app.extract.client import GarminClient
from app.load.raw_writer import RawJsonWriter


def extract_daily_health_range(
    client: GarminClient,
    writer: RawJsonWriter,
    start_date: date,
    end_date: date,
) -> list[Path]:
    paths: list[Path] = []
    current = start_date
    while current <= end_date:
        current_str = current.isoformat()
        payload = {
            "calendar_date": current_str,
            "stats": client.call("get_stats", current_str),
            "heart_rates": client.call("get_heart_rates", current_str),
            "stress": client.call("get_stress_data", current_str),
        }
        path = writer.write("daily_health", current_str, payload)
        paths.append(path)
        current += timedelta(days=1)
    return paths
