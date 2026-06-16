from __future__ import annotations

from typing import Any


def _match(doc: dict[str, Any], filter: dict[str, Any]) -> bool:
    """Check if a doc matches a filter dict (supports $in operator)."""
    for k, v in filter.items():
        sk = str(k)
        if sk not in doc:
            return False
        if isinstance(v, dict) and "$in" in v:
            if doc[sk] not in v["$in"]:
                return False
        elif isinstance(v, dict) and "$ne" in v:
            if doc[sk] == v["$ne"]:
                return False
        elif doc[sk] != v:
            return False
    return True


def _doc_key(filter: dict[str, Any]) -> str | None:
    """Derive a unique doc key from the filter."""
    for k in (
        "stock_item_id",
        "payment_id",
        "menu_id",
        "kitchen_item_id",
        "item_id",
        "order_id",
    ):
        if k in filter:
            return str(filter[k])
    if "correlation_id" in filter:
        return str(filter["correlation_id"])
    return None


class _MockCollection:
    """Stateful mock Mongo collection backed by a shared store dict."""

    def __init__(self, store: dict[str, dict[str, dict[str, Any]]], name: str) -> None:
        self._store = store
        self._name = name
        self._filter: dict[str, Any] = {}
        self._projection: dict[str, Any] = {}
        self._sort_key: str | None = None
        self._sort_dir: int = 1
        self._limit: int | None = None

    async def update_one(
        self,
        filter: dict[str, Any],
        update: dict[str, Any],
        upsert: bool = False,
        **kwargs: Any,
    ) -> None:
        key = _doc_key(filter)
        if not key:
            # Fallback: find matching document
            matched_key = None
            coll = self._store.setdefault(self._name, {})
            for k, doc in coll.items():
                if _match(doc, filter):
                    matched_key = k
                    break
            if matched_key:
                existing = coll[matched_key]
                if "$set" in update:
                    existing.update(update["$set"])
            return

        coll = self._store.setdefault(self._name, {})
        existing = coll.get(key, {})
        # Apply $set
        if "$set" in update:
            existing.update(update["$set"])
        # Apply $setOnInsert (only if upsert and document is new)
        if upsert and "$setOnInsert" in update and key not in coll:
            existing.update(update["$setOnInsert"])
        coll[key] = existing

    async def replace_one(self, filter: dict[str, Any], doc: dict[str, Any], **kwargs: Any) -> None:
        key = _doc_key(filter)
        if key:
            self._store.setdefault(self._name, {})[key] = doc

    async def insert_one(self, doc: dict[str, Any], **kwargs: Any) -> None:
        import uuid

        key = _doc_key(doc) or doc.get("_id")
        if not key:
            key = str(uuid.uuid4())
            doc["_id"] = key
        self._store.setdefault(self._name, {})[key] = doc

    async def delete_one(self, filter: dict[str, Any]) -> None:
        key = _doc_key(filter)
        if key and key in self._store.get(self._name, {}):
            del self._store[self._name][key]

    async def find_one(
        self, filter: dict[str, Any], projection: dict[str, Any] | None = None
    ) -> dict[str, Any] | None:
        for doc in self._store.get(self._name, {}).values():
            if _match(doc, filter):
                if projection:
                    return {k: v for k, v in doc.items() if k not in projection}
                return dict(doc)
        return None

    async def to_list(self, length: int | None = None) -> list[dict[str, Any]]:
        docs = list(self._store.get(self._name, {}).values())
        filtered = docs
        if self._filter:
            filtered = [d for d in docs if _match(d, self._filter)]

        if self._sort_key:

            def get_val(d: dict[str, Any]) -> Any:
                key = self._sort_key
                return d.get(key, "") if key is not None else ""

            filtered.sort(key=get_val, reverse=(self._sort_dir == -1))

        if self._limit is not None:
            filtered = filtered[: self._limit]
        elif length is not None:
            filtered = filtered[:length]

        return filtered

    def find(
        self, filter: dict[str, Any], projection: dict[str, Any] | None = None
    ) -> _MockCollection:
        self._filter = filter
        self._projection = projection or {}
        return self

    def sort(self, key: str, direction: int = 1) -> _MockCollection:
        self._sort_key = key
        self._sort_dir = direction
        return self

    def limit(self, limit: int) -> _MockCollection:
        self._limit = limit
        return self


class _MockDB:
    """Stateful mock Mongo DB backed by a shared store dict."""

    def __init__(self, store: dict[str, dict[str, dict[str, Any]]]) -> None:
        self._store = store

    def __getitem__(self, name: str) -> _MockCollection:
        return _MockCollection(self._store, name)


def make_mock_db() -> tuple[dict[str, dict[str, dict[str, Any]]], _MockDB]:
    """Creates a stateful mock MongoDB for integration tests.

    Returns (store, mock_db) where store is a dict you can inspect/pre-populate.
    """
    store: dict[str, dict[str, dict[str, Any]]] = {}
    return store, _MockDB(store)
