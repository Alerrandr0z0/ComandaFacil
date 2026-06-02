from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from app.menu.domain.category import Category


class MenuItem:
    def __init__(
        self,
        id: int,
        name: str,
        description: str,
        category: Category,
        image_url: str | None = None,
        is_available: bool = True,
    ) -> None:
        self.id: Final[int] = id
        self.name: str = name
        self.description: str = description
        self.category: Category = category
        self.image_url: str | None = image_url
        self.is_available: bool = is_available

    def update_availability(self, is_available: bool) -> None:
        self.is_available = is_available

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id}, name={self.name!r}, "
            f"category={self.category!r}, available={self.is_available})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MenuItem):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class Menu:
    """
    Menu (Aggregate Root) representing a restaurant menu.

    Attributes:
        id: Unique identifier of the menu.
        name: Display name of the menu.
        description: Optional description text.
        is_active: Whether the menu is currently published.
        items: List of MenuItem entities.
    """

    def __init__(
        self,
        id: int,
        name: str,
        description: str = "",
        is_active: bool = True,
    ) -> None:
        self.id: Final[int] = id
        self.name: str = name
        self.description: str = description
        self.is_active: bool = is_active
        self.items: list[MenuItem] = []

    def add_item(self, item: MenuItem) -> None:
        if any(existing.id == item.id for existing in self.items):
            raise ValueError(f"Item com id {item.id} já existe no cardápio.")
        self.items.append(item)

    def remove_item(self, item_id: int) -> None:
        for i, item in enumerate(self.items):
            if item.id == item_id:
                self.items.pop(i)
                return
        raise ValueError(f"Item com id {item_id} não encontrado no cardápio.")

    def update_item(self, item_id: int, **kwargs: str | bool | Category | None) -> MenuItem:
        for item in self.items:
            if item.id == item_id:
                for key, value in kwargs.items():
                    setattr(item, key, value)
                return item
        raise ValueError(f"Item com id {item_id} não encontrado no cardápio.")

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
        if not isinstance(other, Menu):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class MenuRepository(ABC):
    @abstractmethod
    async def find_by_id(self, id: int) -> Menu | None: ...

    @abstractmethod
    async def find_all(self) -> list[Menu]: ...

    @abstractmethod
    async def save(self, menu: Menu) -> None: ...

    @abstractmethod
    async def delete(self, id: int) -> None: ...
