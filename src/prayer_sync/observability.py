"""Structured logs and Prometheus metrics for Yaad's long-running backend."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from time import perf_counter

from prometheus_client import Counter, Gauge, Histogram


class JsonFormatter(logging.Formatter):
    """Render application records as one JSON object per line."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        if record.getMessage() and getattr(record, "event", None) != record.getMessage():
            payload["message"] = record.getMessage()
        for key in ("request_id", "method", "route", "status", "duration_seconds", "trigger", "operation", "provider", "target", "outcome", "error_type"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging() -> None:
    """Configure all process logs once, using JSON suitable for container logs."""
    level_name = os.environ.get("YAAD_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)


def log_event(logger: logging.Logger, level: int, event: str, **fields: object) -> None:
    """Log a named event. Callers must pass only non-sensitive fields."""
    logger.log(level, event, extra={"event": event, **fields})


HTTP_REQUESTS = Counter(
    "yaad_http_requests_total",
    "HTTP requests completed by the API.",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "yaad_http_request_duration_seconds",
    "Time spent handling API requests.",
    ("method", "route"),
)
OPERATIONS = Counter(
    "yaad_operations_total",
    "Prayer provider and calendar operations completed.",
    ("operation", "provider", "target", "outcome"),
)
OPERATION_DURATION = Histogram(
    "yaad_operation_duration_seconds",
    "Time spent in prayer provider and calendar operations.",
    ("operation", "provider", "target", "outcome"),
)
CALENDAR_EVENTS = Counter(
    "yaad_calendar_event_operations_total",
    "Calendar event upserts and deletes completed.",
    ("target", "operation", "outcome"),
)
SYNC_RUNS = Counter(
    "yaad_sync_runs_total",
    "Daily fetch-and-sync runs completed.",
    ("trigger", "outcome"),
)
SYNC_DURATION = Histogram(
    "yaad_sync_run_duration_seconds",
    "Time spent in a complete daily fetch-and-sync run.",
    ("trigger", "outcome"),
)
LAST_SYNC_ATTEMPT = Gauge(
    "yaad_last_sync_attempt_timestamp_seconds",
    "Unix timestamp of the most recent daily sync attempt.",
)
LAST_SUCCESSFUL_SYNC = Gauge(
    "yaad_last_successful_sync_timestamp_seconds",
    "Unix timestamp of the most recent successful daily sync.",
)
LAST_SYNC_HEALTH = Gauge(
    "yaad_last_sync_healthy",
    "Whether the most recent daily sync succeeded (1) or failed (0).",
)


def observe_operation(
    operation: str, *, provider: str = "none", target: str = "none", outcome: str, duration_seconds: float
) -> None:
    OPERATIONS.labels(operation, provider, target, outcome).inc()
    OPERATION_DURATION.labels(operation, provider, target, outcome).observe(duration_seconds)


def observe_calendar_event(target: str, operation: str, outcome: str) -> None:
    CALENDAR_EVENTS.labels(target, operation, outcome).inc()


def observe_daily_run(status: dict, trigger: str, duration_seconds: float) -> None:
    outcome = "success" if status.get("ok") else "failure"
    SYNC_RUNS.labels(trigger, outcome).inc()
    SYNC_DURATION.labels(trigger, outcome).observe(duration_seconds)
    update_sync_freshness(status)


def update_sync_freshness(status: dict) -> None:
    """Restore/update the durable freshness gauges from a last-run record."""
    ran_at = _timestamp(status.get("ran_at"))
    if ran_at is not None:
        LAST_SYNC_ATTEMPT.set(ran_at)
        LAST_SYNC_HEALTH.set(1 if status.get("ok") else 0)
    succeeded_at = _timestamp(status.get("last_success_at"))
    if succeeded_at is not None:
        LAST_SUCCESSFUL_SYNC.set(succeeded_at)


def _timestamp(value: object) -> float | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value).timestamp()
    except ValueError:
        return None


def started_at() -> float:
    return perf_counter()
