from __future__ import annotations

from typing import Final

from app.kitchen.domain.states import IKitchenItemState, Ready, Waiting


class KitchenOrderItem:
    """Aggregate Root representing an item sent to be prepared in the kitchen (KDS)."""

    def __init__(
        self,
        id: int,
        correlation_id: int,
        name_cpy: str,
        station_type_cpy: str,
        tenant_id: str,
        preparation_profile: str = "STANDARD",
        notes: str = "",
    ) -> None:
        self.id: int = id
        self.correlation_id: int = correlation_id
        self.name_cpy: str = name_cpy
        self.station_type_cpy: str = station_type_cpy
        self.tenant_id: str = tenant_id
        self.preparation_profile: Final[str] = preparation_profile
        self.notes: str = notes
        self._state: IKitchenItemState = Waiting()

    @property
    def state(self) -> IKitchenItemState:
        return self._state

    def prepare(self) -> None:
        if self.preparation_profile == "NO_PREP":
            raise ValueError("Item does not require preparation (NO_PREP profile).")
        self._state.prepare(self)

    def mark_as_ready(self) -> None:
        if self.preparation_profile == "NO_PREP" and self._state.name == "WAITING":
            self._state = Ready()
        elif self.preparation_profile == "STANDARD" and self._state.name == "WAITING":
            raise ValueError("Item requires preparation (PREPARING) before READY.")
        else:
            self._state.mark_as_ready(self)

    def cancel(self) -> None:
        self._state.cancel(self)

    def __repr__(self) -> str:
        return (
            f"KitchenOrderItem(id={self.id}, correlation_id={self.correlation_id}, "
            f"name_cpy={self.name_cpy!r}, state={self.state.name}, "
            f"preparation_profile={self.preparation_profile})"
        )
