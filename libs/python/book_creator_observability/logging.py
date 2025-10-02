"""Centralised logging configuration helpers."""

from __future__ import annotations

import json
import logging
import logging.config
import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Iterator


_LOG_CONTEXT: ContextVar[Dict[str, Any]] = ContextVar("book_creator_log_context", default={})
_CONFIGURED: ContextVar[bool] = ContextVar("book_creator_log_configured", default=False)


class ContextFilter(logging.Filter):
    """Inject contextual fields captured via :func:`log_context`."""

    def __init__(self, service_name: str) -> None:
        super().__init__()
        self.service_name = service_name

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401 - inherited docstring
        context = _LOG_CONTEXT.get()
        if context:
            record.observability_context = context
            for key, value in context.items():
                setattr(record, key, value)
        if getattr(record, "service", None) is None:
            record.service = self.service_name
        return True


class JsonFormatter(logging.Formatter):
    """Render log records as structured JSON for downstream aggregation."""

    _RESERVED = {
        "args",
        "asctime",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "thread",
        "threadName",
    }

    _WHITELIST = {
        "service",
        "stage",
        "agent",
        "provider",
        "project_id",
        "run_id",
        "request_id",
        "route",
        "method",
        "status_code",
        "prompt_tokens",
        "completion_tokens",
        "latency_ms",
        "cost_usd",
    }

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - inherited docstring
        message = record.getMessage()
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
        }

        context = getattr(record, "observability_context", {})
        if isinstance(context, dict):
            for key, value in context.items():
                if value is not None:
                    payload.setdefault(key, value)

        for key in self._WHITELIST:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value

        # Include additional extras that are JSON serialisable.
        for key, value in record.__dict__.items():
            if key in self._RESERVED or key in payload or key in self._WHITELIST:
                continue
            if key.startswith("_" ):
                continue
            if self._is_json_safe(value):
                payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)
        return json.dumps(payload, ensure_ascii=True)

    @staticmethod
    def _is_json_safe(value: Any) -> bool:
        try:
            json.dumps(value)
        except (TypeError, ValueError):
            return False
        return True


def setup_logging(
    service_name: str,
    level: str | int = "INFO",
    *,
    capture_warnings: bool | None = None,
) -> None:
    """Configure JSON logging for the current process.

    The configuration is idempotent per process; subsequent calls simply adjust
    the log level while preserving handlers.
    """

    already_configured = _CONFIGURED.get()
    handlers = ["default"]
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": "book_creator_observability.logging.JsonFormatter",
            }
        },
        "filters": {
            "context": {
                "()": "book_creator_observability.logging.ContextFilter",
                "service_name": service_name,
            }
        },
        "handlers": {
            "default": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": "json",
                "filters": ["context"],
            }
        },
        "root": {
            "level": level,
            "handlers": handlers,
        },
        "loggers": {
            "uvicorn": {"handlers": handlers, "level": level, "propagate": False},
            "uvicorn.error": {"handlers": handlers, "level": level, "propagate": False},
            "uvicorn.access": {"handlers": handlers, "level": level, "propagate": False},
        },
    }

    logging.config.dictConfig(config)

    if capture_warnings is None:
        capture_env = os.getenv("BOOK_CREATOR_CAPTURE_WARNINGS")
        capture = (
            capture_env.lower() in {"1", "true", "t", "yes", "y"}
            if capture_env
            else False
        )
    else:
        capture = capture_warnings

    if capture:
        logging.captureWarnings(True)

    if not already_configured:
        _CONFIGURED.set(True)


@contextmanager
def log_context(**kwargs: Any) -> Iterator[None]:
    """Temporarily bind contextual information that should accompany logs."""

    current = _LOG_CONTEXT.get()
    updated = dict(current)
    for key, value in kwargs.items():
        if value is None:
            updated.pop(key, None)
        else:
            updated[key] = value
    token = _LOG_CONTEXT.set(updated)
    try:
        yield
    finally:
        _LOG_CONTEXT.reset(token)
