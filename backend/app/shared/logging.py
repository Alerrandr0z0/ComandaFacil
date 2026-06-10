import json
import logging
import sys
from datetime import UTC, datetime

from app.settings import Settings
from app.shared.tenant_context import get_current_tenant_id


class TenantAwareJsonFormatter(logging.Formatter):
    """Formats log records as JSON, injecting tenant_id from context."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": datetime.now(tz=UTC).isoformat(),
            "lvl": record.levelname,
            "tid": get_current_tenant_id() or "-",
            "msg": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exc"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


class DevFormatter(logging.Formatter):
    """Compact human-readable formatter for development."""

    def format(self, record: logging.LogRecord) -> str:
        tid = get_current_tenant_id() or "-"
        msg = record.getMessage()
        if record.levelno >= logging.ERROR:
            return f"[{record.levelname}] [{tid}] {msg}"
        if record.levelno >= logging.WARNING:
            return f"[{record.levelname}] [{tid}] {msg}"
        return f"  [{tid}] {msg}"


def _silence_noisy_loggers() -> None:
    """Raise levels of chatty loggers to reduce noise in development."""
    for name in (
        "sqlalchemy.engine",
        "sqlalchemy.engine.Engine",
        "sqlalchemy.pool",
        "sqlalchemy.dialects",
        "uvicorn.access",
        "uvicorn.error",
        "watchfiles",
    ):
        logging.getLogger(name).setLevel(logging.WARNING)


def setup_logging(settings: Settings) -> None:
    """Configure application logging.

    In production, outputs compact JSON lines to stdout.
    In development, uses a compact human-readable format.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(TenantAwareJsonFormatter() if settings.is_production else DevFormatter())
    root_logger.addHandler(handler)

    _silence_noisy_loggers()
