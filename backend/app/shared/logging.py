import json
import logging
import logging.handlers
from datetime import UTC, datetime
from pathlib import Path

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


class TenantFileRouter(logging.Handler):
    """Routes log records to the appropriate franchise log file."""

    def __init__(self, log_dir: str, when: str = "midnight", backup_count: int = 30) -> None:
        super().__init__()
        self.log_dir = Path(log_dir)
        self.when = when
        self.backup_count = backup_count
        self._handlers: dict[str, logging.handlers.TimedRotatingFileHandler] = {}
        self.setFormatter(TenantAwareJsonFormatter())

    def _get_handler(self, tenant_id: str) -> logging.handlers.TimedRotatingFileHandler:
        if tenant_id not in self._handlers:
            tenant_dir = self.log_dir / tenant_id
            tenant_dir.mkdir(parents=True, exist_ok=True)
            handler = logging.handlers.TimedRotatingFileHandler(
                filename=tenant_dir / "app.log",
                when=self.when,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            handler.setFormatter(TenantAwareJsonFormatter())
            self._handlers[tenant_id] = handler
        return self._handlers[tenant_id]

    def emit(self, record: logging.LogRecord) -> None:
        tenant_id = get_current_tenant_id() or "system"
        handler = self._get_handler(tenant_id)
        handler.emit(record)


def setup_logging(settings: Settings) -> None:
    """Configure application logging with tenant routing."""
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    # Console handler (for development visibility)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(TenantAwareJsonFormatter())
    root_logger.addHandler(console_handler)

    # Tenant-aware file router (writes to logs/franquias/<tenant_id>/app.log)
    file_router = TenantFileRouter(
        log_dir=settings.log_dir,
        when=settings.log_rotation_when,
        backup_count=settings.log_backup_count,
    )
    root_logger.addHandler(file_router)
