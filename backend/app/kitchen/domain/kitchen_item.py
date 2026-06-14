from __future__ import annotations

from typing import TYPE_CHECKING, Final

from app.kitchen.domain.kitchen_events import KitchenItemCreated, KitchenItemStatusChanged
from app.kitchen.domain.states import IKitchenItemState, Ready, Waiting

if TYPE_CHECKING:
    from app.shared.domain_events import DomainEvent


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
        self._events: list[DomainEvent] = []
        self._events.append(
            KitchenItemCreated(
                item_id=id,
                tenant_id=tenant_id,
                correlation_id=correlation_id,
                name=name_cpy,
                station_type=station_type_cpy,
                notes=notes,
            )
        )

    @property
    def state(self) -> IKitchenItemState:
        return self._state

    def _record_status_change(self, old_state: str, new_state: str) -> None:
        if old_state != new_state:
            self._events.append(
                KitchenItemStatusChanged(
                    item_id=self.id,
                    tenant_id=self.tenant_id,
                    correlation_id=self.correlation_id,
                    name=self.name_cpy,
                    old_state=old_state,
                    new_state=new_state,
                )
            )

    def collect_events(self) -> list[DomainEvent]:
        events = list(self._events)
        self._events.clear()
        return events

    def prepare(self) -> None:
        if self.preparation_profile == "NO_PREP":
            raise ValueError("Item does not require preparation (NO_PREP profile).")
        old_name = self._state.name
        self._state.prepare(self)
        self._record_status_change(old_name, self._state.name)

    def mark_as_ready(self) -> None:
        old_name = self._state.name
        if self.preparation_profile == "NO_PREP" and self._state.name == "WAITING":
            self._state = Ready()
        elif self.preparation_profile == "STANDARD" and self._state.name == "WAITING":
            raise ValueError("Item requires preparation (PREPARING) before READY.")
        else:
            self._state.mark_as_ready(self)
        self._record_status_change(old_name, self._state.name)

    def cancel(self) -> None:
        old_name = self._state.name
        self._state.cancel(self)
        self._record_status_change(old_name, self._state.name)

    def reclaim(self, new_correlation_id: int) -> None:
        if self._state.name != "SURPLUS":
            raise ValueError("Only surplus items can be reclaimed.")
        old_name = self._state.name
        self.correlation_id = new_correlation_id
        self._state = Ready()
        self._record_status_change(old_name, self._state.name)

    def __repr__(self) -> str:
        return (
            f"KitchenOrderItem(id={self.id}, correlation_id={self.correlation_id}, "
            f"name_cpy={self.name_cpy!r}, state={self.state.name}, "
            f"preparation_profile={self.preparation_profile})"
        )
