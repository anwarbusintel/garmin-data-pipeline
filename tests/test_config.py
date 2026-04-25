from __future__ import annotations

from app.utils.config import PROJECT_ROOT, _as_bool, get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_as_bool_uses_default_for_none() -> None:
    assert _as_bool(None, True) is True
    assert _as_bool(None, False) is False


def test_as_bool_recognizes_truthy_and_falsey_values() -> None:
    assert _as_bool("yes", False) is True
    assert _as_bool("on", False) is True
    assert _as_bool("0", True) is False
    assert _as_bool("false", True) is False


def test_get_settings_uses_defaults(monkeypatch) -> None:
    for key in (
        "GARMIN_EMAIL",
        "GARMIN_PASSWORD",
        "GARMIN_TOKEN_DIR",
        "GARMIN_DISABLE_ENV_PROXY",
        "GARMIN_MFA_ENABLED",
        "GARMIN_MFA_CODE",
        "RAW_DATA_DIR",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(key, raising=False)

    _clear_settings_cache()
    settings = get_settings()

    assert settings.raw_data_dir == (PROJECT_ROOT / "data/raw").resolve()
    assert settings.garmin_token_dir == (PROJECT_ROOT / ".garminconnect").resolve()
    assert settings.postgres_host == "localhost"
    assert settings.postgres_port == 5432
    assert settings.postgres_db == "garmin_sleep"
    assert settings.postgres_user == "garmin"
    assert settings.postgres_password == "garmin"
    assert settings.garmin_disable_env_proxy is True
    assert settings.garmin_mfa_enabled is True

    _clear_settings_cache()


def test_get_settings_respects_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("GARMIN_EMAIL", "user@example.com")
    monkeypatch.setenv("GARMIN_PASSWORD", "secret")
    monkeypatch.setenv("GARMIN_TOKEN_DIR", "tokens")
    monkeypatch.setenv("GARMIN_DISABLE_ENV_PROXY", "false")
    monkeypatch.setenv("GARMIN_MFA_ENABLED", "0")
    monkeypatch.setenv("GARMIN_MFA_CODE", " 123456 ")
    monkeypatch.setenv("RAW_DATA_DIR", "custom/raw")
    monkeypatch.setenv("POSTGRES_HOST", "db.local")
    monkeypatch.setenv("POSTGRES_PORT", "5544")
    monkeypatch.setenv("POSTGRES_DB", "analytics")
    monkeypatch.setenv("POSTGRES_USER", "tester")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pw")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    _clear_settings_cache()
    settings = get_settings()

    assert settings.garmin_email == "user@example.com"
    assert settings.garmin_password == "secret"
    assert settings.garmin_token_dir == (PROJECT_ROOT / "tokens").resolve()
    assert settings.garmin_disable_env_proxy is False
    assert settings.garmin_mfa_enabled is False
    assert settings.garmin_mfa_code == "123456"
    assert settings.raw_data_dir == (PROJECT_ROOT / "custom/raw").resolve()
    assert settings.postgres_host == "db.local"
    assert settings.postgres_port == 5544
    assert settings.postgres_db == "analytics"
    assert settings.postgres_user == "tester"
    assert settings.postgres_password == "pw"
    assert settings.log_level == "DEBUG"

    _clear_settings_cache()
