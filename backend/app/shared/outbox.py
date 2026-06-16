from __future__ import annotations

import asyncio
import contextlib
import datetime
import json
import logging
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Integer, String, Text, select
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_orm import Base

if TYPE_CHECKING:
    from motor.motor_asyncio import AsyncIOMotorDatabase
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger("app.shared.outbox")


# ─── ORM Model ─────────────────────────────────────────────────────────────────


class OutboxEntry(Base):
    """Persistent outbox entry for reliable MongoDB read-model sync."""

    __tablename__ = "outbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    aggregate_type: Mapped[str] = mapped_column(String(100), nullable=False)
    aggregate_id: Mapped[str] = mapped_column(String(100), nullable=False)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False)
    last_attempt_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __init__(self, **kw: Any) -> None:
        kw.setdefault("retry_count", 0)
        kw.setdefault("status", "pending")
        kw.setdefault("created_at", datetime.datetime.now(datetime.UTC))
        super().__init__(**kw)

    def __repr__(self) -> str:
        return (
            f"OutboxEntry(id={self.id}, event={self.event_type!r}, "
            f"aggregate={self.aggregate_type}:{self.aggregate_id}, "
            f"status={self.status!r})"
        )


# ─── Writer ────────────────────────────────────────────────────────────────────


class OutboxWriter:
    """Writes outbox entries into the current DB session.

    Must be called *before* commit so the entry participates
    in the same PG transaction as the business data.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_entry(
        self,
        aggregate_type: str,
        aggregate_id: str,
        event_type: str,
        payload: str,
    ) -> None:
        entry = OutboxEntry(
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            event_type=event_type,
            payload=payload,
            created_at=datetime.datetime.now(datetime.UTC),
            status="pending",
        )
        self._session.add(entry)


# ─── Event → outbox mapping ───────────────────────────────────────────────────


def serialize_event_for_outbox(event: Any) -> dict[str, str] | None:
    """Convert a domain event to outbox fields or None if not syncable."""
    event_type = type(event).__name__

    # Order events
    if hasattr(event, "order_id"):
        return {
            "aggregate_type": "order",
            "aggregate_id": str(event.order_id),
            "event_type": f"order.{_event_name(event_type)}",
            "payload": json.dumps(
                {
                    "order_id": str(event.order_id),
                    "tenant_id": str(getattr(event, "tenant_id", "")),
                    "event_type": event_type,
                }
            ),
        }

    # Stock events
    if hasattr(event, "item_id"):
        return {
            "aggregate_type": "stock",
            "aggregate_id": str(event.item_id),
            "event_type": f"stock.{_event_name(event_type)}",
            "payload": json.dumps(
                {
                    "item_id": str(event.item_id),
                    "tenant_id": str(getattr(event, "tenant_id", "")),
                    "event_type": event_type,
                }
            ),
        }

    return None


def _event_name(class_name: str) -> str:
    """Convert PascalCase event class name to snake_case.

    OrderItemAdded → order_item_added
    """
    result = [class_name[0].lower()]
    for c in class_name[1:]:
        if c.isupper():
            result.append("_")
            result.append(c.lower())
        else:
            result.append(c)
    return "".join(result)


# ─── Consumer ──────────────────────────────────────────────────────────────────


class OutboxConsumer:
    """Background worker that polls the outbox table and writes to MongoDB.

    Runs as an asyncio task inside the application process.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        mongo_db: AsyncIOMotorDatabase,  # type: ignore[type-arg]
        *,
        poll_interval: float = 1.0,
        batch_size: int = 10,
        max_retries: int = 3,
    ) -> None:
        self._session_factory = session_factory
        self._mongo = mongo_db
        self._poll_interval = poll_interval
        self._batch_size = batch_size
        self._max_retries = max_retries
        self._running = False
        self._task: asyncio.Task[None] | None = None

    # ── Lifecycle ──────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info("OutboxConsumer started (poll_interval=%ss)", self._poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("OutboxConsumer stopped")

    # ── Poll loop ──────────────────────────────────────────────────────────

    async def _poll_loop(self) -> None:
        while self._running:
            try:
                await self._process_batch()
            except Exception:
                logger.exception("Outbox consumer error — will retry on next poll")
            await asyncio.sleep(self._poll_interval)

    async def _process_batch(self) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(OutboxEntry)
                .where(OutboxEntry.status == "pending")
                .order_by(OutboxEntry.created_at)
                .limit(self._batch_size)
            )
            entries = list(result.scalars().all())

            if not entries:
                return

            for entry in entries:
                await session.refresh(entry)
                if entry.status != "pending":
                    continue
                await self._process_entry(entry, session)

    async def _process_entry(
        self,
        entry: OutboxEntry,
        session: AsyncSession,
    ) -> None:
        try:
            await self._sync_to_mongo(entry)
            entry.status = "completed"
        except Exception as exc:
            entry.retry_count += 1
            entry.last_attempt_at = datetime.datetime.now(datetime.UTC)
            entry.error_message = str(exc)
            if entry.retry_count >= self._max_retries:
                entry.status = "failed"
                logger.exception(
                    "Outbox entry %d permanently failed after %d retries",
                    entry.id,
                    self._max_retries,
                )
            else:
                logger.warning(
                    "Outbox entry %d failed (retry %d/%d): %s",
                    entry.id,
                    entry.retry_count,
                    self._max_retries,
                    exc,
                )
        await session.commit()

    # ── Mongo sync ─────────────────────────────────────────────────────────

    async def _sync_to_mongo(self, entry: OutboxEntry) -> None:
        """Route an outbox entry to the correct MongoDB collection/operation.

        Supports two payload formats:

        **Snapshot** (event_type = ``*.snapshot`` or ``*.sync``)::

            {"collection": "stock_read",
             "filter": {"stock_item_id": 1, "tenant_id": "t1"},
             "document": {"stock_item_id": 1, "tenant_id": "t1", "name": "..."}}

            → collection.replace_one(filter, document, upsert=True)

        **Delete** (event_type = ``*.delete``)::

            {"collection": "stock_read",
             "filter": {"stock_item_id": 1, "tenant_id": "t1"}}

            → collection.delete_one(filter)

        **Legacy** (auto-mapped domain events)::

            → collection.replace_one({aggregate_type, aggregate_id, event_type},
                                      {**payload, synced_at}, upsert=True)
        """
        try:
            payload = json.loads(entry.payload)
        except json.JSONDecodeError:
            logger.exception("Outbox entry %d has invalid JSON payload", entry.id)
            raise

        event_suffix = (
            entry.event_type.split(".")[-1] if "." in entry.event_type else entry.event_type
        )

        # --- Snapshot / pre-computed document ---------------------------------
        if event_suffix in ("snapshot", "sync"):
            collection_name = payload.get("collection")
            if collection_name is None:
                logger.warning("Snapshot entry %d missing 'collection' in payload", entry.id)
                return
            collection = self._mongo[collection_name]
            doc: dict[str, object] = {
                **payload["document"],
                "synced_at": datetime.datetime.now(datetime.UTC).isoformat(),
            }
            await collection.replace_one(payload["filter"], doc, upsert=True)
            return

        # --- Delete -----------------------------------------------------------
        if event_suffix == "delete":
            collection_name = payload.get("collection")
            if collection_name is None:
                logger.warning("Delete entry %d missing 'collection' in payload", entry.id)
                return
            collection = self._mongo[collection_name]
            await collection.delete_one(payload["filter"])
            return

        # --- Legacy (auto-mapped domain events) --------------------------------
        collection = self._mongo["audit_events"]

        doc = {
            **payload,
            "aggregate_type": entry.aggregate_type,
            "aggregate_id": entry.aggregate_id,
            "event_type": entry.event_type,
            "synced_at": datetime.datetime.now(datetime.UTC).isoformat(),
        }

        await collection.replace_one(
            {
                "aggregate_type": entry.aggregate_type,
                "aggregate_id": entry.aggregate_id,
                "event_type": entry.event_type,
            },
            doc,
            upsert=True,
        )
