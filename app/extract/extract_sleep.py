from __future__ import annotations

from datetime import date
from pathlib import Path

from app.extract.client import GarminClient
from app.load.raw_writer import RawJsonWriter


def extract_sleep_range(
    client: GarminClient,
    writer: RawJsonWriter,
    start_date: date,
    end_date: date,
) -> list[Path]:
    paths: list[Path] = []
    current = start_date
    while current <= end_date:
        current_str = current.isoformat()
        payload = client.call("get_sleep_data", current_str)
        path = writer.write("sleep", current_str, payload)
        paths.append(path)
        current = date.fromordinal(current.toordinal() + 1)
    return paths
