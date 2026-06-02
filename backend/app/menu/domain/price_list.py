from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from app.shared.money import Money


class PriceListItem:
    """
    Entity representing a single price entry within a PriceList.

    Attributes:
        id: Unique identifier of the price list item.
        price_list_id: Reference to the parent PriceList.
        menu_item_id: Reference to the MenuItem being priced.
        price: The monetary price for the item.
    """

    def __init__(
        self,
        id: int,
        price_list_id: int,
        menu_item_id: int,
        price: Money,
    ) -> None:
        self.id: Final[int] = id
        self.price_list_id: Final[int] = price_list_id
        self.menu_item_id: Final[int] = menu_item_id
        self.price: Money = price

    def update_price(self, new_price: Money) -> None:
        self.price = new_price

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id}, menu_item_id={self.menu_item_id}, "
            f"price={self.price!r})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PriceListItem):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class PriceList:
    """
    PriceList (Aggregate Root) for managing pricing schemes.

    Attributes:
        id: Unique identifier of the price list.
        name: Display name (e.g. "Regular", "Happy Hour").
        description: Optional description.
        is_active: Whether this price list is currently in effect.
        valid_from: Start date of validity.
        valid_until: Optional end date of validity (None = indefinite).
        items: List of PriceListItem entities.
    """

    def __init__(
        self,
        id: int,
        name: str,
        description: str = "",
        is_active: bool = True,
        valid_from: datetime.datetime | None = None,
        valid_until: datetime.datetime | None = None,
    ) -> None:
        self.id: Final[int] = id
        self.name: str = name
        self.description: str = description
        self.is_active: bool = is_active
        self.valid_from: datetime.datetime = valid_from or datetime.datetime.now(datetime.UTC)
        self.valid_until: datetime.datetime | None = valid_until
        self.items: list[PriceListItem] = []

    def add_item(self, item: PriceListItem) -> None:
        if any(existing.menu_item_id == item.menu_item_id for existing in self.items):
            raise ValueError(f"Item de menu {item.menu_item_id} já possui preço nesta lista.")
        self.items.append(item)

    def remove_item(self, menu_item_id: int) -> None:
        for i, item in enumerate(self.items):
            if item.menu_item_id == menu_item_id:
                self.items.pop(i)
                return
        raise ValueError(f"Item de menu {menu_item_id} não encontrado nesta lista de preços.")

    def get_price(self, menu_item_id: int) -> Money | None:
        for item in self.items:
            if item.menu_item_id == menu_item_id:
                return item.price
        return None

    def is_valid_now(self, reference: datetime.datetime | None = None) -> bool:
        now = reference or datetime.datetime.now(datetime.UTC)
        if self.valid_from and now < self.valid_from:
            return False
        return not (self.valid_until and now > self.valid_until)

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id}, name={self.name!r}, "
            f"items={len(self.items)}, active={self.is_active})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PriceList):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class PriceListRepository(ABC):
    @abstractmethod
    async def find_by_id(self, id: int) -> PriceList | None: ...

    @abstractmethod
    async def find_active(self) -> list[PriceList]: ...

    @abstractmethod
    async def find_all(self) -> list[PriceList]: ...

    @abstractmethod
    async def save(self, price_list: PriceList) -> None: ...

    @abstractmethod
    async def delete(self, id: int) -> None: ...
