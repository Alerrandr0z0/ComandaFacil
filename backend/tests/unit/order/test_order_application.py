from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING

import pytest

from app.order.application.commands import (
    CancelOrderItemCommand,
    CancelOrderItemHandler,
)
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.shared.money import Money

if TYPE_CHECKING:
    from app.order.domain.repository import OrderRepository


@dataclass
class FakeOrderRepository:
    _orders: dict[tuple[int, str], OrderForm] = field(default_factory=dict)

    async def find_by_id(self, id: int, tenant_id: str) -> OrderForm | None:
        return self._orders.get((id, tenant_id))

    async def save(self, order: OrderForm) -> None:
        self._orders[(order.id, order.tenant_id)] = order


class TestCancelOrderItem:
    async def test_handle_when_item_exists_then_marks_as_canceled(self) -> None:
        # Arrange
        repo: OrderRepository = FakeOrderRepository()  # type: ignore[abstract]
        order = OrderForm(id=1, tenant_id="franquia_001")
        item = OrderFormItem(
            id=10,
            menu_item_id=100,
            name_cpy="Pizza",
            price_cpy=Money(Decimal("39.90")),
            station_type_cpy="Grill",
            quantity=1,
        )
        order.add_item(item)
        await repo.save(order)
        handler = CancelOrderItemHandler(repo)

        # Act
        updated_order = await handler.handle(
            CancelOrderItemCommand(order_id=1, item_id=10, tenant_id="franquia_001")
        )

        # Assert
        canceled_item = next(i for i in updated_order.items if i.id == 10)
        assert canceled_item.status.value == "CANCELED"

    async def test_handle_when_order_not_found_then_raises_not_found(self) -> None:
        # Arrange
        repo: OrderRepository = FakeOrderRepository()  # type: ignore[abstract]
        handler = CancelOrderItemHandler(repo)

        # Act & Assert
        with pytest.raises(Exception, match="não encontrado"):
            await handler.handle(
                CancelOrderItemCommand(order_id=999, item_id=10, tenant_id="franquia_001")
            )

    async def test_handle_when_item_not_found_then_raises_not_found(self) -> None:
        # Arrange
        repo: OrderRepository = FakeOrderRepository()  # type: ignore[abstract]
        order = OrderForm(id=1, tenant_id="franquia_001")
        await repo.save(order)
        handler = CancelOrderItemHandler(repo)

        # Act & Assert
        with pytest.raises(Exception, match="não encontrado"):
            await handler.handle(
                CancelOrderItemCommand(order_id=1, item_id=999, tenant_id="franquia_001")
            )
