from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from app.utils.config import Settings

LOGGER = logging.getLogger(__name__)


class PipelineRunLogger:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def start_run(
        self,
        pipeline_name: str,
        details: dict[str, Any] | None = None,
    ) -> UUID:
        run_id = uuid4()
        query = (
            "INSERT INTO pipeline_run_log (run_id, pipeline_name, status, details) "
            "VALUES (%s, %s, %s, %s)"
        )
        self._execute(
            query,
            (
                run_id,
                pipeline_name,
                "started",
                Jsonb(details or {}),
            ),
            action="start",
            pipeline_name=pipeline_name,
        )
        return run_id

    def finish_success(
        self,
        run_id: UUID,
        details: dict[str, Any] | None = None,
    ) -> None:
        query = (
            "UPDATE pipeline_run_log "
            "SET status = %s, "
            "    finished_at = NOW(), "
            "    error_message = NULL, "
            "    details = COALESCE(details, '{}'::jsonb) || %s "
            "WHERE run_id = %s"
        )
        self._execute(
            query,
            (
                "success",
                Jsonb(details or {}),
                run_id,
            ),
            action="mark success",
        )

    def finish_failure(
        self,
        run_id: UUID,
        error_message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        query = (
            "UPDATE pipeline_run_log "
            "SET status = %s, "
            "    finished_at = NOW(), "
            "    error_message = %s, "
            "    details = COALESCE(details, '{}'::jsonb) || %s "
            "WHERE run_id = %s"
        )
        self._execute(
            query,
            (
                "failed",
                error_message,
                Jsonb(details or {}),
                run_id,
            ),
            action="mark failure",
        )

    def _execute(
        self,
        query: str,
        params: tuple[object, ...],
        *,
        action: str,
        pipeline_name: str | None = None,
    ) -> None:
        try:
            with psycopg.connect(self._settings.postgres_dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, params)
                conn.commit()
        except Exception as exc:
            if pipeline_name:
                LOGGER.warning(
                    "Unable to %s pipeline run log for %s: %s",
                    action,
                    pipeline_name,
                    exc,
                )
            else:
                LOGGER.warning("Unable to %s pipeline run log: %s", action, exc)
