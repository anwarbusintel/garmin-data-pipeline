from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any

from app.utils.config import Settings


PROXY_ENV_VARS = (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
    "no_proxy",
    "GIT_HTTP_PROXY",
    "GIT_HTTPS_PROXY",
)


class GarminClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    def login(self) -> Any:
        if self._client is not None:
            return self._client

        if not self._settings.garmin_email or not self._settings.garmin_password:
            raise ValueError("GARMIN_EMAIL and GARMIN_PASSWORD must be set before login.")

        from garminconnect import Garmin

        self._settings.garmin_token_dir.mkdir(parents=True, exist_ok=True)
        prompt_mfa = self._prompt_mfa if self._settings.garmin_mfa_enabled else None
        client = Garmin(
            self._settings.garmin_email,
            self._settings.garmin_password,
            prompt_mfa=prompt_mfa,
        )
        with self._without_env_proxy():
            client.login(str(self._settings.garmin_token_dir))
        self._client = client
        return client

    def call(self, method_name: str, *args: Any, **kwargs: Any) -> Any:
        client = self.login()
        method = getattr(client, method_name, None)
        if method is None:
            raise AttributeError(f"Garmin client has no method named {method_name!r}.")
        with self._without_env_proxy():
            return method(*args, **kwargs)

    def available_methods(self) -> list[str]:
        client = self.login()
        return sorted(name for name in dir(client) if not name.startswith("_"))

    def _prompt_mfa(self) -> str:
        if self._settings.garmin_mfa_code:
            return self._settings.garmin_mfa_code
        raise RuntimeError(
            "Garmin MFA is enabled but GARMIN_MFA_CODE is not set. "
            "Add a current one-time code to .env and retry."
        )

    @contextmanager
    def _without_env_proxy(self):
        if not self._settings.garmin_disable_env_proxy:
            yield
            return

        previous_values = {name: os.environ.pop(name, None) for name in PROXY_ENV_VARS}
        try:
            yield
        finally:
            for name, value in previous_values.items():
                if value is not None:
                    os.environ[name] = value
