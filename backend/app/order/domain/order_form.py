from __future__ import annotations

from typing import TYPE_CHECKING

from app.order.domain.states import Closed, IOrderState, Open
from app.shared.money import Money

if TYPE_CHECKING:
    from app.order.domain.fulfillment import IFulfillmentStrategy
    from app.order.domain.order_item import OrderFormItem


class OrderForm:
    def __init__(self, id: int, tenant_id: str, display_code: str = "") -> None:
        self.id: int = id
        self.tenant_id: str = tenant_id
        self.display_code: str = display_code or str(id)
        self._items: list[OrderFormItem] = []
        self._state: IOrderState = Open()
        self.fulfillment_strategy: IFulfillmentStrategy | None = None
        self._payment_requested: bool = False

    @property
    def items(self) -> list[OrderFormItem]:
        return self._items

    @property
    def state(self) -> IOrderState:
        return self._state

    def set_fulfillment_strategy(self, strategy: IFulfillmentStrategy) -> None:
        self.fulfillment_strategy = strategy

    def add_item(self, item: OrderFormItem) -> None:
        self._state.add_item(self, item)

    def request_payment(self) -> None:
        self._state.request_payment(self)

    def process_payment(self) -> None:
        self._state.process_payment(self)

    def cancel(self) -> None:
        self._state.cancel(self)

    def deliver(self) -> None:
        if self._state.name != "PAID":
            raise ValueError("Cannot deliver order unless it is paid.")
        if self.fulfillment_strategy is None:
            raise ValueError("Fulfillment strategy must be set before delivery.")

        self.fulfillment_strategy.deliver(self)
        self._state = Closed()

    def total(self) -> Money:
        # Soma do subtotal de todos os itens
        subtotal = Money.zero()
        for item in self._items:
            subtotal += item.calculate_subtotal()

        # Adiciona a taxa da estratégia de atendimento se definida
        if self.fulfillment_strategy is not None:
            subtotal += self.fulfillment_strategy.calculate_fee()

        return subtotal

    def __repr__(self) -> str:
        return f"OrderForm(id={self.id}, tenant_id={self.tenant_id!r}, display_code={self.display_code!r}, state={self.state.name})"
