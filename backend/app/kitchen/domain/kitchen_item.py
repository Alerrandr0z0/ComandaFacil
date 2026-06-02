from __future__ import annotations

from app.kitchen.domain.states import IKitchenItemState, Waiting


class KitchenOrder_Item:  # noqa: N801
    """Aggregate Root representing an item sent to be prepared in the kitchen (KDS)."""

    def __init__(
        self,
        id: int,
        correlation_id: int,
        name_cpy: str,
        station_type_cpy: str,
        tenant_id: str,
    ) -> None:
        self.id: int = id
        self.correlation_id: int = correlation_id
        self.name_cpy: str = name_cpy
        self.station_type_cpy: str = station_type_cpy
        self.tenant_id: str = tenant_id
        self._state: IKitchenItemState = Waiting()

    @property
    def state(self) -> IKitchenItemState:
        """Returns the current state of the kitchen item."""
        return self._state

    def prepare(self) -> None:
        """Starts preparing the item, transitioning state to PREPARING."""
        self._state.prepare(self)

    def mark_as_ready(self) -> None:
        """Marks the preparation as completed, transitioning state to READY."""
        self._state.mark_as_ready(self)

    def cancel(self) -> None:
        """Cancels preparation, transitioning state to CANCELLED."""
        self._state.cancel(self)

    def __repr__(self) -> str:
        return (
            f"KitchenOrder_Item(id={self.id}, correlation_id={self.correlation_id}, "
            f"name_cpy={self.name_cpy!r}, state={self.state.name})"
        )
