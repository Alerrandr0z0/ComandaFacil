from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.shared.domain_events import DomainEvent


@dataclass(frozen=True)
class KitchenItemStatusChanged(DomainEvent):
    item_id: int
    tenant_id: str
    correlation_id: int
    name: str
    old_state: str
    new_state: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class KitchenItemCreated(DomainEvent):
    item_id: int
    tenant_id: str
    correlation_id: int
    name: str
    station_type: str
    notes: str = ""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
