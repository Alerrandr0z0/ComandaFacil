from __future__ import annotations


class DomainEvent:
    """Base class for all domain events in the system.

    Subclasses MUST be decorated with @dataclass(frozen=True) and
    include an ``occurred_at: datetime = field(default_factory=...)`` field.
    """

    def __repr__(self) -> str:
        occurred = getattr(self, "occurred_at", None)
        ts = occurred.isoformat() if occurred else "unknown"
        return f"{type(self).__name__}(occurred_at={ts})"
