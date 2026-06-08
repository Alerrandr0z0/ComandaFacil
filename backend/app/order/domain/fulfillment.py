from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

from app.order.domain.delivery_states import (
    AwaitingPickup,
    Delivered,
    FailedDelivery,
    IDeliveryState,
    InTransit,
)
from app.order.domain.enums import FulfillmentStatus
from app.shared.money import Money

if TYPE_CHECKING:
    from app.order.domain.order_form import OrderForm
    from app.shared.value_objects import Address


class IFulfillmentStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def deliver(self, order: OrderForm) -> None:
        pass

    @abstractmethod
    def validate(self) -> bool:
        pass

    @abstractmethod
    def get_status(self) -> FulfillmentStatus:
        pass

    @abstractmethod
    def calculate_fee(self) -> Money:
        pass


class Table(IFulfillmentStrategy):
    def __init__(self, table_num: int) -> None:
        if table_num < 1:
            raise ValueError(f"Table number must be at least 1, got: {table_num}")
        self.table_num: int = table_num
        self._status: FulfillmentStatus = FulfillmentStatus.READY_FOR_PICKUP

    @property
    def name(self) -> str:
        return "TABLE"

    def deliver(self, order: OrderForm) -> None:  # noqa: ARG002
        self._status = FulfillmentStatus.DELIVERED

    def validate(self) -> bool:
        return self.table_num >= 1

    def get_status(self) -> FulfillmentStatus:
        return self._status

    def calculate_fee(self) -> Money:
        return Money.zero()


class Takeaway(IFulfillmentStrategy):
    def __init__(self, customer_name: str) -> None:
        if not customer_name or not customer_name.strip():
            raise ValueError("Customer name cannot be empty for takeaway orders.")
        self.customer_name: str = customer_name
        self._status: FulfillmentStatus = FulfillmentStatus.READY_FOR_PICKUP

    @property
    def name(self) -> str:
        return "TAKEAWAY"

    def deliver(self, order: OrderForm) -> None:  # noqa: ARG002
        self._status = FulfillmentStatus.DELIVERED

    def validate(self) -> bool:
        return bool(self.customer_name)

    def get_status(self) -> FulfillmentStatus:
        return self._status

    def calculate_fee(self) -> Money:
        return Money.zero()


class Delivery(IFulfillmentStrategy):
    def __init__(self, address: Address, estimated_time: int = 40, tracking_code: int = 0) -> None:
        self.address: Address = address
        self.estimated_time: int = estimated_time
        self.tracking_code: int = tracking_code
        self._state: IDeliveryState = AwaitingPickup()

    @property
    def name(self) -> str:
        return "DELIVERY"

    @property
    def state(self) -> IDeliveryState:
        return self._state

    def dispatch(self) -> None:
        self._state.dispatch(self)

    def deliver(self, order: OrderForm) -> None:  # noqa: ARG002
        self._state.deliver(self)

    def fail(self) -> None:
        self._state.fail(self)

    def validate(self) -> bool:
        return self.address is not None  # type: ignore[reportUnnecessaryComparison]

    def get_status(self) -> FulfillmentStatus:
        if isinstance(self._state, AwaitingPickup):
            return FulfillmentStatus.READY_FOR_PICKUP
        if isinstance(self._state, InTransit):
            return FulfillmentStatus.SHIPPED
        if isinstance(self._state, Delivered):
            return FulfillmentStatus.DELIVERED
        if isinstance(self._state, FailedDelivery):
            return FulfillmentStatus.RETURNED
        raise ValueError(f"Unknown delivery state: {self._state}")

    def calculate_fee(self) -> Money:
        # Taxa de entrega fixa do ComandaFácil
        return Money(Decimal("7.00"))
