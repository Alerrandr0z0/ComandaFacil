from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.shared.domain_events import DomainEvent


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class PriceListCreated(DomainEvent):
    price_list_id: int
    tenant_id: str
    name: str
    occurred_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class PriceListUpdated(DomainEvent):
    price_list_id: int
    tenant_id: str
    name: str
    is_active: bool
    occurred_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class PriceListDeleted(DomainEvent):
    price_list_id: int
    tenant_id: str
    occurred_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class PriceListItemAdded(DomainEvent):
    price_list_id: int
    menu_item_id: int
    price_amount: float
    tenant_id: str
    occurred_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class PriceListItemRemoved(DomainEvent):
    price_list_id: int
    menu_item_id: int
    tenant_id: str
    occurred_at: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class PriceListItemUpdated(DomainEvent):
    price_list_id: int
    menu_item_id: int
    old_price_amount: float
    new_price_amount: float
    tenant_id: str
    occurred_at: datetime = field(default_factory=_utc_now)
