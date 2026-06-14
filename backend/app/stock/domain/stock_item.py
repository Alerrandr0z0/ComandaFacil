from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING, Final, Protocol, runtime_checkable

from app.stock.domain.enums import TransactionType
from app.stock.domain.measured_quantity import MeasuredQuantity
from app.stock.domain.stock_events import StockAdjusted, StockTransactionRegistered

if TYPE_CHECKING:
    from app.shared.domain_events import DomainEvent
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
        self.id: int = id
        self.tenant_id: Final[str] = tenant_id
        self.name: str = name
        self.category: str = category
        self.min_stock_level: float = min_stock_level
        self.is_active: bool = is_active
        self.transactions: list[StockTransaction] = transactions or []
        self._events: list[DomainEvent] = []

    def add_event(self, event: DomainEvent) -> None:
        self._events.append(event)

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    @abstractmethod
    def get_balance(self) -> MeasuredQuantity:
        pass

    @abstractmethod
    def get_unit_cost(self) -> Decimal:
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

    def add_transaction(self, tx: StockTransaction) -> None:
        # Calculate old balance before adding the transaction
        old_balance = self.get_balance()

        super().add_transaction(tx)

        # Raise domain events
        if tx.type == TransactionType.ADJUSTMENT:
            self._events.append(
                StockAdjusted(
                    item_id=self.id,
                    tenant_id=self.tenant_id,
                    name=self.name,
                    old_quantity=old_balance.value,
                    new_quantity=tx.quantity.value,
                    unit=self.unit,
                    reason=tx.reason,
                )
            )
        else:
            self._events.append(
                StockTransactionRegistered(
                    item_id=self.id,
                    tenant_id=self.tenant_id,
                    name=self.name,
                    quantity=tx.quantity.value,
                    unit=tx.quantity.unit,
                    transaction_type=tx.type.name,
                    cost_amount=tx.cost_amount,
                    reason=tx.reason,
                )
            )

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

    def get_unit_cost(self) -> Decimal:
        input_txs = [
            tx
            for tx in self.transactions
            if tx.type == TransactionType.INPUT and tx.cost_amount > Decimal("0.0")
        ]
        if not input_txs:
            return Decimal("0.0")

        total_cost = sum(
            (tx.quantity.value * tx.cost_amount for tx in input_txs),
            Decimal("0.0"),
        )
        total_qty = sum((tx.quantity.value for tx in input_txs), Decimal("0.0"))

        if total_qty <= Decimal("0.0"):
            return Decimal("0.0")

        return total_cost / total_qty


class CompositeStockItem(StockItem):
    """Composite item composed of other stock items."""

    def __init__(
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

    def add_transaction(self, tx: StockTransaction) -> None:  # noqa: ARG002
        raise ValueError(
            "Transações diretas não são permitidas em itens compostos. "
            "Ajuste os componentes individualmente."
        )

    def get_balance(self) -> MeasuredQuantity:
        # Balance is ALWAYS derived purely from children — no ledger on the composite itself
        balance = MeasuredQuantity(Decimal("0"), self.unit)
        for comp in self.components:
            balance = balance.add(comp.get_balance())
        return balance

    def get_unit_cost(self) -> Decimal:
        # O custo unitário do item composto é a soma recursiva dos custos de seus componentes
        return sum((comp.get_unit_cost() for comp in self.components), Decimal("0.0"))


@runtime_checkable
class StockItemRepository(Protocol):
    async def find_by_id(self, id: int, tenant_id: str) -> StockItem | None: ...
    async def find_by_name(self, name: str, tenant_id: str) -> StockItem | None: ...
    async def find_all(self, tenant_id: str) -> list[StockItem]: ...
    async def find_low_stock(self, tenant_id: str) -> list[StockItem]: ...
    async def save(self, item: StockItem) -> None: ...
    async def delete(self, id: int, tenant_id: str) -> None: ...
