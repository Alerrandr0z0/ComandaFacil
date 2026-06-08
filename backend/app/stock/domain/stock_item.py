from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING, Final, Protocol, runtime_checkable

from app.stock.domain.enums import TransactionType
from app.stock.domain.measured_quantity import MeasuredQuantity

if TYPE_CHECKING:
    from app.stock.domain.transaction import StockTransaction


class StockItem(ABC):
    """Abstract Base Class representing a tracked inventory item."""

    def __init__(
        self,
        id: int,
        tenant_id: str,
        name: str,
        category: str,
        min_stock_level: float = 0.0,
        is_active: bool = True,
        transactions: list[StockTransaction] | None = None,
    ) -> None:
        self.id: Final[int] = id
        self.tenant_id: Final[str] = tenant_id
        self.name: str = name
        self.category: str = category
        self.min_stock_level: float = min_stock_level
        self.is_active: bool = is_active
        self.transactions: list[StockTransaction] = transactions or []

    @abstractmethod
    def get_balance(self) -> MeasuredQuantity:
        pass

    def add_transaction(self, tx: StockTransaction) -> None:
        self.transactions.append(tx)

    @property
    def is_low_stock(self) -> bool:
        return self.get_balance().amount < self.min_stock_level

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    def set_min_stock_level(self, level: float) -> None:
        if level < 0:
            raise ValueError(f"Minimum stock level cannot be negative, got: {level}")
        self.min_stock_level = level

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id}, name={self.name!r}, "
            f"qty={self.get_balance()}, min={self.min_stock_level}, "
            f"active={self.is_active})"
        )


class SimpleStockItem(StockItem):
    """Standard inventory item tracked by transaction ledger."""

    def __init__(
        self,
        id: int,
        tenant_id: str,
        name: str,
        category: str,
        unit: str,
        min_stock_level: float = 0.0,
        is_active: bool = True,
        transactions: list[StockTransaction] | None = None,
    ) -> None:
        super().__init__(id, tenant_id, name, category, min_stock_level, is_active, transactions)
        self.unit: str = unit

    def get_balance(self) -> MeasuredQuantity:
        # Sort transactions to process them chronologically
        sorted_txs = sorted(self.transactions, key=lambda tx: tx.occurred_at)

        latest_adjustment = None
        adj_idx = -1
        for i, tx in enumerate(sorted_txs):
            if tx.type == TransactionType.ADJUSTMENT:
                latest_adjustment = tx
                adj_idx = i

        if latest_adjustment:
            balance = latest_adjustment.quantity
        else:
            balance = MeasuredQuantity(Decimal("0"), self.unit)

        for tx in sorted_txs[adj_idx + 1 :]:
            if tx.type in (TransactionType.INPUT, TransactionType.PRODUCTION):
                balance = balance.add(tx.quantity)
            elif tx.type in (TransactionType.OUTPUT, TransactionType.WASTE):
                balance = balance.subtract(tx.quantity)

        return balance


class CompositeStockItem(StockItem):
    """Composite item composed of other stock items."""

    def __init__(  # noqa: PLR0913
        self,
        id: int,
        tenant_id: str,
        name: str,
        category: str,
        unit: str,
        min_stock_level: float = 0.0,
        is_active: bool = True,
        components: list[StockItem] | None = None,
        transactions: list[StockTransaction] | None = None,
    ) -> None:
        super().__init__(id, tenant_id, name, category, min_stock_level, is_active, transactions)
        self.unit: str = unit
        self.components: list[StockItem] = components or []

    def add_component(self, item: StockItem) -> None:
        self.components.append(item)

    def get_balance(self) -> MeasuredQuantity:
        # Aggregate components balance
        balance = MeasuredQuantity(Decimal("0"), self.unit)
        for comp in self.components:
            balance = balance.add(comp.get_balance())

        # Apply its own transaction ledger (if any)
        sorted_txs = sorted(self.transactions, key=lambda tx: tx.occurred_at)
        latest_adjustment = None
        adj_idx = -1
        for i, tx in enumerate(sorted_txs):
            if tx.type == TransactionType.ADJUSTMENT:
                latest_adjustment = tx
                adj_idx = i

        if latest_adjustment:
            balance = latest_adjustment.quantity

        for tx in sorted_txs[adj_idx + 1 :]:
            if tx.type in (TransactionType.INPUT, TransactionType.PRODUCTION):
                balance = balance.add(tx.quantity)
            elif tx.type in (TransactionType.OUTPUT, TransactionType.WASTE):
                balance = balance.subtract(tx.quantity)

        return balance


@runtime_checkable
class StockItemRepository(Protocol):
    async def find_by_id(self, id: int, tenant_id: str) -> StockItem | None: ...
    async def find_by_name(self, name: str, tenant_id: str) -> StockItem | None: ...
    async def find_all(self, tenant_id: str) -> list[StockItem]: ...
    async def find_low_stock(self, tenant_id: str) -> list[StockItem]: ...
    async def save(self, item: StockItem) -> None: ...
    async def delete(self, id: int, tenant_id: str) -> None: ...
