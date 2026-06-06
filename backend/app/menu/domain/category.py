from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CategoryItem:
    menu_item_id: int


class Category:
    def __init__(self, name: str, items: list[CategoryItem] | None = None) -> None:
        if not name or not name.strip():
            raise ValueError("Nome da categoria não pode ser vazio.")
        self.name: str = name
        self.items: list[CategoryItem] = items or []

    def add_item(self, menu_item_id: int) -> None:
        if any(item.menu_item_id == menu_item_id for item in self.items):
            raise ValueError(f"Item com id {menu_item_id} já existe nesta categoria.")
        self.items.append(CategoryItem(menu_item_id))

    def remove_item(self, menu_item_id: int) -> None:
        for i, item in enumerate(self.items):
            if item.menu_item_id == menu_item_id:
                self.items.pop(i)
                return
        raise ValueError(f"Item com id {menu_item_id} não encontrado nesta categoria.")

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Category(name={self.name!r}, items={len(self.items)})"
