from __future__ import annotations

from datetime import date

import pytest

from app.extract import run_recent


def test_extract_date_range_rejects_reversed_dates() -> None:
    with pytest.raises(ValueError, match="end_date must be on or after start_date"):
        run_recent.extract_date_range(
            client=object(),
            writer=object(),
            start_date=date(2026, 4, 24),
            end_date=date(2026, 4, 23),
        )


def test_extract_recent_range_rejects_days_less_than_one() -> None:
    with pytest.raises(ValueError, match="days must be at least 1"):
        run_recent.extract_recent_range(
            client=object(),
            writer=object(),
            days=0,
        )


def test_extract_recent_range_converts_days_into_expected_dates(monkeypatch) -> None:
    class FakeDate(date):
        @classmethod
        def today(cls) -> "FakeDate":
            return cls(2026, 4, 24)

    captured: dict[str, object] = {}

    def fake_extract_date_range(client, writer, start_date, end_date, include_hrv=True):
        captured["client"] = client
        captured["writer"] = writer
        captured["start_date"] = start_date
        captured["end_date"] = end_date
        captured["include_hrv"] = include_hrv
        return {"sleep": [], "daily_health": [], "activities": [], "hrv": []}

    monkeypatch.setattr(run_recent, "date", FakeDate)
    monkeypatch.setattr(run_recent, "extract_date_range", fake_extract_date_range)

    client = object()
    writer = object()
    results = run_recent.extract_recent_range(client=client, writer=writer, days=3, include_hrv=False)

    assert results == {"sleep": [], "daily_health": [], "activities": [], "hrv": []}
    assert captured == {
        "client": client,
        "writer": writer,
        "start_date": date(2026, 4, 22),
        "end_date": date(2026, 4, 24),
        "include_hrv": False,
    }
