import json
import logging
from datetime import UTC, datetime
from typing import Any

SENSITIVE_KEYS = frozenset({"authorization", "cookie", "password", "secret", "token"})


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    return any(fragment in normalized for fragment in SENSITIVE_KEYS)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if is_sensitive_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in (
            "correlation_id",
            "run_id",
            "worker_id",
            "user_id",
            "event_type",
            "outbox_id",
            "attempt",
            "assigned_count",
            "method",
            "path",
            "status_code",
            "error_code",
        ):
            if value := getattr(record, key, None):
                data[key] = value
        if "correlation_id" not in data:
            from runscope_api.middleware import correlation_id_context

            if correlation_id := correlation_id_context.get():
                data["correlation_id"] = correlation_id
        if isinstance(record.exc_info, tuple) and record.exc_info[1]:
            data["exception_type"] = type(record.exc_info[1]).__name__
        return json.dumps(redact(data), default=str, separators=(",", ":"))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
