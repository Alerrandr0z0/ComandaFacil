from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import TYPE_CHECKING

from app.order.domain.delivery_states import AwaitingPickup, IDeliveryState
from app.order.domain.enums import FulfillmentStatus
from app.shared.money import Money

if TYPE_CHECKING:
    from app.order.domain.order_form import OrderForm
    from app.shared.value_objects import Address, TableNum


class IFulfillmentStratrgy(ABC):
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


class Table(IFulfillmentStratrgy):
    def __init__(self, table_num: TableNum) -> None:
        self.table_num: TableNum = table_num
        self._status: FulfillmentStatus = FulfillmentStatus.PENDING

    @property
    def name(self) -> str:
        return "TABLE"

    def deliver(self, order: OrderForm) -> None:  # noqa: ARG002
        # Entrega imediata na mesa: muda status para SUCCESS
        self._status = FulfillmentStatus.SUCCESS

    def validate(self) -> bool:
        return self.table_num is not None  # type: ignore[reportUnnecessaryComparison]

    def get_status(self) -> FulfillmentStatus:
        return self._status

    def calculate_fee(self) -> Money:
        # Mesa não tem taxa extra de entrega
        return Money.zero()


class Takeaway(IFulfillmentStratrgy):
    def __init__(self, customer_name: str) -> None:
        if not customer_name or not customer_name.strip():
            raise ValueError("Customer name cannot be empty for takeaway orders.")
        self.customer_name: str = customer_name
        self._status: FulfillmentStatus = FulfillmentStatus.PENDING

    @property
    def name(self) -> str:
        return "TAKEAWAY"

    def deliver(self, order: OrderForm) -> None:  # noqa: ARG002
        # Entrega por retirada: muda status para SUCCESS
        self._status = FulfillmentStatus.SUCCESS

    def validate(self) -> bool:
        return bool(self.customer_name)

    def get_status(self) -> FulfillmentStatus:
        return self._status

    def calculate_fee(self) -> Money:
        return Money.zero()


class Delivery(IFulfillmentStratrgy):
    def __init__(self, address: Address, estimated_time: int = 40, tracking_code: int = 0) -> None:
        self.address: Address = address
        self.estimated_time: int = estimated_time
        self.tracking_code: int = tracking_code
        self._state: IDeliveryState = AwaitingPickup()
        self._status: FulfillmentStatus = FulfillmentStatus.PENDING

    @property
    def name(self) -> str:
        return "DELIVERY"

    @property
    def state(self) -> IDeliveryState:
        return self._state

    def dispatch(self) -> None:
        self._state.dispatch(self)
        self._status = FulfillmentStatus.IN_PROGRESS

    def deliver(self, order: OrderForm) -> None:  # noqa: ARG002
        self._state.deliver(self)
        self._status = FulfillmentStatus.SUCCESS

    def fail(self) -> None:
        self._state.fail(self)
        self._status = FulfillmentStatus.FAILED

    def validate(self) -> bool:
        return self.address is not None  # type: ignore[reportUnnecessaryComparison]

    def get_status(self) -> FulfillmentStatus:
        return self._status

    def calculate_fee(self) -> Money:
        # Taxa de entrega fixa do ComandaFácil
        return Money(Decimal("7.00"))
