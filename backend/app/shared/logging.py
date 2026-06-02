import json
import logging
from datetime import UTC, datetime

from app.settings import Settings
from app.shared.tenant_context import get_current_tenant_id


class TenantAwareJsonFormatter(logging.Formatter):
    """Formats log records as JSON, injecting tenant_id from context."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "level": record.levelname,
            "tenant_id": get_current_tenant_id() or "system",
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log_entry.update(record.extra)  # type: ignore[arg-type]
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(settings: Settings) -> None:
    """Configure application logging with stdout structured JSON logs."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Console handler (for centralized stdout structured logs)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(TenantAwareJsonFormatter())
    root_logger.addHandler(console_handler)
