from __future__ import annotations

import logging
from contextvars import ContextVar
from typing import Any, ClassVar

logger = logging.getLogger("app.shared.domain_events")


class DomainEvent:
    """Base class for all domain events in the system.

    Subclasses MUST be decorated with @dataclass(frozen=True) and
    include an ``occurred_at: datetime = field(default_factory=...)`` field.
    """

    def __repr__(self) -> str:
        occurred = getattr(self, "occurred_at", None)
        ts = occurred.isoformat() if occurred else "unknown"
        return f"{type(self).__name__}(occurred_at={ts})"


# ContextVar to accumulate events during the lifecycle of a request/session
pending_events_var: ContextVar[list[DomainEvent] | None] = ContextVar(
    "pending_events", default=None
)


def register_pending_events(events: list[DomainEvent]) -> None:
    """Registers domain events raised during the transaction to be dispatched on successful commit."""
    if not events:
        return
    try:
        pending_list = pending_events_var.get()
        if pending_list is None:
            pending_list = []
            pending_events_var.set(pending_list)
        pending_list.extend(events)
    except LookupError:
        # Fallback if no context is active
        pass


class EventBus:
    """Central async Event Bus for registering subscribers and publishing domain events."""

    _listeners: ClassVar[dict[type[DomainEvent], list[Any]]] = {}

    @classmethod
    def register(cls, event_type: type[DomainEvent], handler: Any) -> None:
        """Subscribes an async handler to a specific domain event type."""
        handlers = cls._listeners.setdefault(event_type, [])
        if handler not in handlers:
            handlers.append(handler)

    @classmethod
    async def publish(cls, event: DomainEvent) -> None:
        """Publishes a domain event asynchronously to all registered handlers."""
        handlers = cls._listeners.get(type(event), [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                # Log or handle handler failures gracefully to avoid breaking transactions
                # (since commit is already complete)
                logger.error(
                    f"Error executing event handler {handler} for {event}: {e}", exc_info=True
                )
