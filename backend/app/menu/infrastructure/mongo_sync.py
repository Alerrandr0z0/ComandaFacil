from __future__ import annotations

from typing import Any


class MenuReadModelSync:
    """Syncs Menu aggregate to MongoDB read model collection."""

    def __init__(self, mongo_db: Any) -> None:
        self._collection = mongo_db["menu_read_models"]

    async def sync(self, doc: dict[str, Any]) -> None:
        await self._collection.replace_one(
            {"menu_id": doc["menu_id"]},
            doc,
            upsert=True,
        )

    async def remove(self, menu_id: int) -> None:
        await self._collection.delete_one({"menu_id": menu_id})
