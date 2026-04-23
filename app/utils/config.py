from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    garmin_email: str
    garmin_password: str
    garmin_token_dir: Path
    garmin_disable_env_proxy: bool
    garmin_mfa_enabled: bool
    garmin_mfa_code: str
    raw_data_dir: Path
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    log_level: str

    @property
    def postgres_dsn(self) -> str:
        return (
            f"host={self.postgres_host} "
            f"port={self.postgres_port} "
            f"dbname={self.postgres_db} "
            f"user={self.postgres_user} "
            f"password={self.postgres_password}"
        )

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    token_dir = (PROJECT_ROOT / os.getenv("GARMIN_TOKEN_DIR", ".garminconnect")).resolve()
    raw_data_dir = (PROJECT_ROOT / os.getenv("RAW_DATA_DIR", "data/raw")).resolve()

    return Settings(
        garmin_email=os.getenv("GARMIN_EMAIL", ""),
        garmin_password=os.getenv("GARMIN_PASSWORD", ""),
        garmin_token_dir=token_dir,
        garmin_disable_env_proxy=_as_bool(os.getenv("GARMIN_DISABLE_ENV_PROXY"), True),
        garmin_mfa_enabled=_as_bool(os.getenv("GARMIN_MFA_ENABLED"), True),
        garmin_mfa_code=os.getenv("GARMIN_MFA_CODE", "").strip(),
        raw_data_dir=raw_data_dir,
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        postgres_db=os.getenv("POSTGRES_DB", "garmin_sleep"),
        postgres_user=os.getenv("POSTGRES_USER", "garmin"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "garmin"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
    )
