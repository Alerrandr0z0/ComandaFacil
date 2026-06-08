from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from app.stock.domain.measured_quantity import MeasuredQuantity
    from app.stock.domain.stock_item import StockItem


class RecipeIngredient:
    def __init__(self, stock_item: StockItem, quantity: MeasuredQuantity) -> None:
        self.stock_item: StockItem = stock_item
        self.quantity: MeasuredQuantity = quantity

    def __repr__(self) -> str:
        return f"RecipeIngredient(item={self.stock_item.name}, qty={self.quantity})"


class Recipe:
    def __init__(
        self,
        id: int,
        menu_item_id: int,
        tenant_id: str,
        ingredients: list[RecipeIngredient] | None = None,
    ) -> None:
        self.id: int = id
        self.menu_item_id: int = menu_item_id
        self.tenant_id: str = tenant_id
        self._ingredients: list[RecipeIngredient] = ingredients or []

    def add_ingredient(self, item: StockItem, quantity: MeasuredQuantity) -> None:
        # Check if already exists, update or append
        for ing in self._ingredients:
            if ing.stock_item.id == item.id:
                # Update quantity
                object.__setattr__(ing, "quantity", quantity)
                return
        self._ingredients.append(RecipeIngredient(item, quantity))

    def get_ingredients(self) -> list[RecipeIngredient]:
        return list(self._ingredients)

    def calculate_total_cost(self) -> float:
        # Cost calculation could resolve menu_item pricing or assume a mock/zero cost base in stock.
        # Let's return a simple double for cost as UML suggests or default 0.0 unless integrated.
        return 0.0

    def __repr__(self) -> str:
        return f"Recipe(id={self.id}, menu_item={self.menu_item_id}, ingredients={len(self._ingredients)})"


@runtime_checkable
class RecipeRepository(Protocol):
    async def find_by_menu_item(self, menu_item_id: int, tenant_id: str) -> Recipe | None: ...

    async def save(self, recipe: Recipe) -> None: ...
