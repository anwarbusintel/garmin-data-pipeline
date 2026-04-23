from __future__ import annotations

from datetime import date
from pathlib import Path

from app.extract.client import GarminClient
from app.load.raw_writer import RawJsonWriter


def extract_activities_range(
    client: GarminClient,
    writer: RawJsonWriter,
    start_date: date,
    end_date: date,
) -> list[Path]:
    start_str = start_date.isoformat()
    end_str = end_date.isoformat()
    activities = client.call("get_activities_by_date", start_str, end_str)
    payload = {
        "start_date": start_str,
        "end_date": end_str,
        "activity_count": len(activities),
        "activities": activities,
    }
    path = writer.write("activities", f"{start_str}_to_{end_str}", payload)
    return [path]
