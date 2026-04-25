from __future__ import annotations

import json
from pathlib import Path

from app.load.raw_writer import RawJsonWriter
from app.utils.config import Settings


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        garmin_email="",
        garmin_password="",
        garmin_token_dir=tmp_path / "tokens",
        garmin_disable_env_proxy=True,
        garmin_mfa_enabled=True,
        garmin_mfa_code="",
        raw_data_dir=tmp_path / "raw",
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="garmin_sleep",
        postgres_user="garmin",
        postgres_password="garmin",
        log_level="INFO",
    )


def test_ensure_directories_creates_expected_dataset_folders(tmp_path: Path) -> None:
    writer = RawJsonWriter(make_settings(tmp_path))

    writer.ensure_directories()

    for dataset in ("sleep", "daily_health", "activities", "hrv"):
        assert (tmp_path / "raw" / dataset).is_dir()


def test_write_sanitizes_record_key_and_persists_payload(tmp_path: Path) -> None:
    writer = RawJsonWriter(make_settings(tmp_path))

    output_path = writer.write(
        dataset="sleep",
        record_key="2026/04/24:night",
        payload={"sleep_score": 82, "notes": ["steady"]},
    )

    assert output_path.exists()
    assert output_path.parent == tmp_path / "raw" / "sleep"
    assert ":" not in output_path.name
    assert "/" not in output_path.name
    assert output_path.suffix == ".json"

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload == {"notes": ["steady"], "sleep_score": 82}
