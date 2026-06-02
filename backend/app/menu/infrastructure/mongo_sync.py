from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.menu.domain.menu import Menu


class MenuReadModelSync:
    """Syncs Menu aggregate to MongoDB read model collection."""

    def __init__(self, mongo_db: Any) -> None:
        self._collection = mongo_db["menu_read_models"]

    async def sync(self, menu: Menu) -> None:
        doc = {
            "menu_id": menu.id,
            "tenant_id": menu.tenant_id,
            "name": menu.name,
            "description": menu.description,
            "is_active": menu.is_active,
            "items": [
                {
                    "id": item.id,
                    "name": item.name,
                    "description": item.description,
                    "category": str(item.category),
                    "image_url": item.image_url,
                    "is_available": item.is_available,
                }
                for item in menu.items
            ],
        }
        await self._collection.replace_one(
            {"menu_id": menu.id},
            doc,
            upsert=True,
        )

    async def remove(self, menu_id: int) -> None:
        await self._collection.delete_one({"menu_id": menu_id})
