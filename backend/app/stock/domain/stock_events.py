from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from app.shared.domain_events import DomainEvent


@dataclass(frozen=True)
class StockItemCreated(DomainEvent):
    item_id: int
    tenant_id: str
    name: str
    category: str
    unit: str
    min_stock_level: float
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class StockAdjusted(DomainEvent):
    item_id: int
    tenant_id: str
    name: str
    old_quantity: Decimal
    new_quantity: Decimal
    unit: str
    reason: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class StockTransactionRegistered(DomainEvent):
    item_id: int
    tenant_id: str
    name: str
    quantity: Decimal
    unit: str
    transaction_type: str  # INPUT, OUTPUT, WASTE, PRODUCTION
    cost_amount: Decimal = Decimal("0.0")
    reason: str = ""
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(frozen=True)
class RecipeSaved(DomainEvent):
    menu_item_id: int
    tenant_id: str
    ingredient_count: int
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
