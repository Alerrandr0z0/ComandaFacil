from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, Final

from app.menu.domain.category import Category

if TYPE_CHECKING:
    from app.shared.money import Money


class PreparationProfile(Enum):
    """Defines the preparation lifecycle for a menu item."""

    NO_PREP = "NO_PREP"  # Waiting → Ready directly (e.g., bottled drinks)
    STANDARD = "STANDARD"  # Waiting → Preparing → Ready (cooked items)

    def __repr__(self) -> str:
        return f"PreparationProfile.{self.name}"


class MenuItem:
    """
    MenuItem (Aggregate Root) representing a catalog item (product) in the system.
    """

    def __init__(
        self,
        id: int,
        tenant_id: str,
        name: str,
        description: str,
        base_price: Money,
        station_type: str,
        category_name: str,
        image_url: str | None = None,
        is_available: bool = True,
        preparation_profile: PreparationProfile = PreparationProfile.STANDARD,
    ) -> None:
        self.id: Final[int] = id
        self.tenant_id: Final[str] = tenant_id
        self.name: str = name
        self.description: str = description
        self.base_price: Money = base_price
        self.station_type: str = station_type
        self.category_name: str = category_name
        self.image_url: str | None = image_url
        self.is_available: bool = is_available
        self.preparation_profile: Final[PreparationProfile] = preparation_profile

    def update_availability(self, is_available: bool) -> None:
        self.is_available = is_available

    def update_details(
        self,
        name: str,
        description: str,
        base_price: Money,
        station_type: str,
        category_name: str,
        image_url: str | None,
    ) -> None:
        self.name = name
        self.description = description
        self.base_price = base_price
        self.station_type = station_type
        self.category_name = category_name
        self.image_url = image_url

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id}, tenant_id={self.tenant_id!r}, "
            f"name={self.name!r}, base_price={self.base_price!r}, available={self.is_available})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MenuItem):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class Menu:
    """
    Menu (Aggregate Root) representing a visual layout of categories and items.
    """

    def __init__(
        self,
        id: int,
        tenant_id: str,
        name: str,
        description: str = "",
        is_active: bool = True,
        price_list_id: int | None = None,
    ) -> None:
        self.id: Final[int] = id
        self.tenant_id: Final[str] = tenant_id
        self.name: str = name
        self.description: str = description
        self.is_active: bool = is_active
        self.price_list_id: int | None = price_list_id
        self.categories: list[Category] = []

    def add_category(self, category_name: str) -> Category:
        if any(c.name.lower() == category_name.lower() for c in self.categories):
            raise ValueError(f"Categoria '{category_name}' já existe neste cardápio.")
        category = Category(name=category_name)
        self.categories.append(category)
        return category

    def remove_category(self, category_name: str) -> None:
        for i, category in enumerate(self.categories):
            if category.name.lower() == category_name.lower():
                self.categories.pop(i)
                return
        raise ValueError(f"Categoria '{category_name}' não encontrada neste cardápio.")

    def add_item_to_category(self, category_name: str, menu_item_id: int) -> None:
        # Find or create category
        category = next(
            (c for c in self.categories if c.name.lower() == category_name.lower()), None
        )
        if not category:
            category = self.add_category(category_name)

        # Check if item already exists in any category of this menu
        for c in self.categories:
            if any(item.menu_item_id == menu_item_id for item in c.items):
                raise ValueError(f"Item com id {menu_item_id} já existe neste cardápio.")

        category.add_item(menu_item_id)

    def remove_item_from_category(self, category_name: str, menu_item_id: int) -> None:
        for category in self.categories:
            if category.name.lower() == category_name.lower():
                category.remove_item(menu_item_id)
                # Clean up empty category
                if not category.items:
                    self.remove_category(category.name)
                return
        raise ValueError(
            f"Item com id {menu_item_id} não encontrado na categoria '{category_name}'."
        )

    def associate_price_list(self, price_list_id: int | None) -> None:
        self.price_list_id = price_list_id

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id}, name={self.name!r}, "
            f"categories={len(self.categories)}, active={self.is_active}, price_list_id={self.price_list_id})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Menu):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


class MenuRepository(ABC):
    @abstractmethod
    async def find_by_id(self, id: int, tenant_id: str) -> Menu | None: ...

    @abstractmethod
    async def find_all(self, tenant_id: str) -> list[Menu]: ...

    @abstractmethod
    async def save(self, menu: Menu) -> None: ...

    @abstractmethod
    async def delete(self, id: int, tenant_id: str) -> None: ...


class MenuItemRepository(ABC):
    @abstractmethod
    async def find_by_id(self, id: int, tenant_id: str) -> MenuItem | None: ...

    @abstractmethod
    async def find_all(self, tenant_id: str) -> list[MenuItem]: ...

    @abstractmethod
    async def save(self, item: MenuItem) -> None: ...

    @abstractmethod
    async def delete(self, id: int, tenant_id: str) -> None: ...
