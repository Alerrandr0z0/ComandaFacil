from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.shared.domain_events import DomainEvent


@dataclass(frozen=True)
class MenuItemCreated(DomainEvent):
    item_id: int
    tenant_id: str
    name: str
    category: str
    price: Decimal
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class MenuItemUpdated(DomainEvent):
    item_id: int
    tenant_id: str
    name: str
    category: str
    price: Decimal
    is_available: bool
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class MenuItemDeleted(DomainEvent):
    item_id: int
    tenant_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
