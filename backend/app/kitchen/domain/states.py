from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.kitchen.domain.kitchen_item import KitchenOrderItem


class IKitchenItemState(ABC):
    """Abstract State interface for kitchen order preparation cycle."""

    @property
    @abstractmethod
    def name(self) -> str:
        """String representation of the state name."""

    @abstractmethod
    def prepare(self, item: KitchenOrderItem) -> None:
        """Transitions item to preparing state."""

    @abstractmethod
    def mark_as_ready(self, item: KitchenOrderItem) -> None:
        """Transitions item to ready/completed state."""

    @abstractmethod
    def cancel(self, item: KitchenOrderItem) -> None:
        """Transitions item to cancelled state."""


class Waiting(IKitchenItemState):
    """Initial state representing item waiting in preparation queue."""

    @property
    def name(self) -> str:
        return "WAITING"

    def prepare(self, item: KitchenOrderItem) -> None:
        item._state = Preparing()  # type: ignore[reportPrivateUsage]

    def mark_as_ready(self, item: KitchenOrderItem) -> None:  # noqa: ARG002
        raise ValueError("Cannot mark item as ready in WAITING state.")

    def cancel(self, item: KitchenOrderItem) -> None:
        item._state = Cancelled()  # type: ignore[reportPrivateUsage]


class Preparing(IKitchenItemState):
    """State representing active preparation of the item."""

    @property
    def name(self) -> str:
        return "PREPARING"

    def prepare(self, item: KitchenOrderItem) -> None:  # noqa: ARG002
        raise ValueError("Item is already being prepared.")

    def mark_as_ready(self, item: KitchenOrderItem) -> None:
        item._state = Ready()  # type: ignore[reportPrivateUsage]

    def cancel(self, item: KitchenOrderItem) -> None:
        item._state = Cancelled()  # type: ignore[reportPrivateUsage]


class Ready(IKitchenItemState):
    """Terminal state representing completed preparation."""

    @property
    def name(self) -> str:
        return "READY"

    def prepare(self, item: KitchenOrderItem) -> None:  # noqa: ARG002
        raise ValueError("Cannot prepare a ready item.")

    def mark_as_ready(self, item: KitchenOrderItem) -> None:  # noqa: ARG002
        raise ValueError("Item already ready.")

    def cancel(self, item: KitchenOrderItem) -> None:  # noqa: ARG002
        raise ValueError("Cannot cancel a ready item.")


class Cancelled(IKitchenItemState):
    """Terminal state representing cancelled preparation."""

    @property
    def name(self) -> str:
        return "CANCELLED"

    def prepare(self, item: KitchenOrderItem) -> None:  # noqa: ARG002
        raise ValueError("Cannot prepare a cancelled item.")

    def mark_as_ready(self, item: KitchenOrderItem) -> None:  # noqa: ARG002
        raise ValueError("Cannot mark a cancelled item as ready.")

    def cancel(self, item: KitchenOrderItem) -> None:  # noqa: ARG002
        raise ValueError("Item already cancelled.")
