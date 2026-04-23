from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from app.extract.client import GarminClient
from app.load.raw_writer import RawJsonWriter


def extract_hrv_range(
    client: GarminClient,
    writer: RawJsonWriter,
    start_date: date,
    end_date: date,
) -> list[Path]:
    paths: list[Path] = []
    current = start_date
    while current <= end_date:
        current_str = current.isoformat()
        payload = client.call("get_hrv_data", current_str)
        if payload is not None:
            path = writer.write("hrv", current_str, payload)
            paths.append(path)
        current += timedelta(days=1)
    return paths
