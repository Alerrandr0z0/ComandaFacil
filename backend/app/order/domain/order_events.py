from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.shared.domain_events import DomainEvent


@dataclass(frozen=True)
class OrderItemAdded(DomainEvent):
    order_id: int
    tenant_id: str
    item_id: int
    menu_item_id: int
    name: str
    quantity: int
    price: Decimal
    notes: str = ""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class OrderCreated(DomainEvent):
    order_id: int
    tenant_id: str
    fulfillment_type: str
    display_code: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
