from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.order.domain.order_form import OrderForm
    from app.order.domain.order_item import OrderFormItem


class IOrderState(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def add_item(self, order: OrderForm, item: OrderFormItem) -> None:
        pass

    @abstractmethod
    def request_payment(self, order: OrderForm) -> None:
        pass

    @abstractmethod
    def process_payment(self, order: OrderForm) -> None:
        pass

    @abstractmethod
    def cancel(self, order: OrderForm) -> None:
        pass


class Open(IOrderState):
    @property
    def name(self) -> str:
        return "OPEN"

    def add_item(self, order: OrderForm, item: OrderFormItem) -> None:
        if order._payment_requested:  # type: ignore[reportPrivateUsage]
            raise ValueError("Cannot add items after payment is requested.")
        order._items.append(item)  # type: ignore[reportPrivateUsage]

    def request_payment(self, order: OrderForm) -> None:
        order._payment_requested = True  # type: ignore[reportPrivateUsage]

    def process_payment(self, order: OrderForm) -> None:
        if not order._payment_requested:  # type: ignore[reportPrivateUsage]
            raise ValueError(
                "Cannot process payment directly in Open state. Payment must be requested first."
            )
        order._state = Paid()  # type: ignore[reportPrivateUsage]

    def cancel(self, order: OrderForm) -> None:
        order._state = Closed()  # type: ignore[reportPrivateUsage]


class Paid(IOrderState):
    @property
    def name(self) -> str:
        return "PAID"

    def add_item(self, order: OrderForm, item: OrderFormItem) -> None:  # noqa: ARG002
        raise ValueError("Cannot add items to a paid order.")

    def request_payment(self, order: OrderForm) -> None:  # noqa: ARG002
        raise ValueError("Payment already requested and paid.")

    def process_payment(self, order: OrderForm) -> None:  # noqa: ARG002
        raise ValueError("Order already paid.")

    def cancel(self, order: OrderForm) -> None:  # noqa: ARG002
        raise ValueError("Cannot cancel a paid order.")


class Closed(IOrderState):
    @property
    def name(self) -> str:
        return "CLOSED"

    def add_item(self, order: OrderForm, item: OrderFormItem) -> None:  # noqa: ARG002
        raise ValueError("Cannot add items to a closed order.")

    def request_payment(self, order: OrderForm) -> None:  # noqa: ARG002
        raise ValueError("Order is closed.")

    def process_payment(self, order: OrderForm) -> None:  # noqa: ARG002
        raise ValueError("Order is closed.")

    def cancel(self, order: OrderForm) -> None:  # noqa: ARG002
        raise ValueError("Cannot cancel a closed order.")
