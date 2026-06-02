from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.order.domain.fulfillment import Delivery


class IDeliveryState(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def dispatch(self, delivery: Delivery) -> None:
        pass

    @abstractmethod
    def deliver(self, delivery: Delivery) -> None:
        pass

    @abstractmethod
    def fail(self, delivery: Delivery) -> None:
        pass


class AwaitingPickup(IDeliveryState):
    @property
    def name(self) -> str:
        return "AWAITING_PICKUP"

    def dispatch(self, delivery: Delivery) -> None:
        delivery._state = InTransit()  # type: ignore[reportPrivateUsage]

    def deliver(self, delivery: Delivery) -> None:  # noqa: ARG002
        raise ValueError("Cannot deliver package before it is dispatched.")

    def fail(self, delivery: Delivery) -> None:  # noqa: ARG002
        raise ValueError("Cannot fail delivery before it is dispatched.")


class InTransit(IDeliveryState):
    @property
    def name(self) -> str:
        return "IN_TRANSIT"

    def dispatch(self, delivery: Delivery) -> None:  # noqa: ARG002
        raise ValueError("Delivery is already in transit.")

    def deliver(self, delivery: Delivery) -> None:
        delivery._state = Delivered()  # type: ignore[reportPrivateUsage]

    def fail(self, delivery: Delivery) -> None:
        delivery._state = FailedDelivery()  # type: ignore[reportPrivateUsage]


class Delivered(IDeliveryState):
    @property
    def name(self) -> str:
        return "DELIVERED"

    def dispatch(self, delivery: Delivery) -> None:  # noqa: ARG002
        raise ValueError("Cannot dispatch a package that has already been delivered.")

    def deliver(self, delivery: Delivery) -> None:  # noqa: ARG002
        raise ValueError("Package has already been delivered.")

    def fail(self, delivery: Delivery) -> None:  # noqa: ARG002
        raise ValueError("Cannot fail a package that has already been delivered.")


class FailedDelivery(IDeliveryState):
    @property
    def name(self) -> str:
        return "FAILED_DELIVERY"

    def dispatch(self, delivery: Delivery) -> None:
        # Re-tentativa permitida: despacha novamente
        delivery._state = InTransit()  # type: ignore[reportPrivateUsage]

    def deliver(self, delivery: Delivery) -> None:  # noqa: ARG002
        raise ValueError("Cannot deliver a failed package. Reprepare or redispatch first.")

    def fail(self, delivery: Delivery) -> None:  # noqa: ARG002
        raise ValueError("Delivery already marked as failed.")
