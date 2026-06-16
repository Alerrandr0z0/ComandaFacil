from collections.abc import AsyncGenerator
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.settings import Settings
from app.shared.domain_events import EventBus, pending_events_var
from app.shared.outbox import OutboxWriter, serialize_event_for_outbox

# ─── PostgreSQL ────────────────────────────────────────────────────────────────

_engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


async def init_postgres(settings: Settings) -> None:
    global _engine, session_factory
    _engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=10,
        max_overflow=20,
    )
    session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def close_postgres() -> None:
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    if session_factory is None:
        raise RuntimeError("PostgreSQL not initialized. Call init_postgres() first.")
    async with session_factory() as session:
        token = pending_events_var.set([])
        original_commit = session.commit

        async def commit_with_events() -> None:
            events = pending_events_var.get()
            if events:
                await _write_outbox_entries(session, events)

            await original_commit()

            if events:
                pending_events_var.set([])
                for event in events:
                    await EventBus.publish(event)

        session.commit = commit_with_events

        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            _reset_pending_events(token)


async def _write_outbox_entries(session: AsyncSession, events: list[Any]) -> None:
    outbox_writer = OutboxWriter(session)
    for event in events:
        mapped = serialize_event_for_outbox(event)
        if mapped is not None:
            await outbox_writer.add_entry(
                aggregate_type=mapped["aggregate_type"],
                aggregate_id=mapped["aggregate_id"],
                event_type=mapped["event_type"],
                payload=mapped["payload"],
            )


def _reset_pending_events(token: Any) -> None:
    try:
        pending_events_var.reset(token)
    except ValueError:
        pending_events_var.set(None)


# ─── MongoDB ──────────────────────────────────────────────────────────────────

_mongo_client: AsyncIOMotorClient | None = None  # type: ignore[type-arg]
_mongo_database: AsyncIOMotorDatabase | None = None  # type: ignore[type-arg]


async def init_mongo(settings: Settings) -> None:
    global _mongo_client, _mongo_database
    _mongo_client = AsyncIOMotorClient(settings.mongo_url)
    _mongo_database = _mongo_client[settings.mongo_db]


async def close_mongo() -> None:
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None


async def ensure_indexes() -> None:
    """Ensure critical MongoDB indexes for performance."""
    if _mongo_database is None:
        return

    # orders_read: tenant_id + created_at (compound for analytics)
    await _mongo_database["orders_read"].create_index([("tenant_id", 1), ("created_at", -1)])
    await _mongo_database["orders_read"].create_index("items.id")

    await _mongo_database["order_history"].create_index([("tenant_id", 1), ("closed_at", -1)])
    # order_id is used for funnel lookups
    await _mongo_database["order_history"].create_index("order_id")

    await _mongo_database["kitchen_read"].create_index([("tenant_id", 1), ("created_at", -1)])

    # stock_read: tenant_id + is_low_stock  # noqa: ERA001
    await _mongo_database["stock_read"].create_index([("tenant_id", 1), ("is_low_stock", 1)])


def get_mongo_db() -> AsyncIOMotorDatabase:  # type: ignore[type-arg]
    if _mongo_database is None:
        raise RuntimeError("MongoDB not initialized. Call init_mongo() first.")
    return _mongo_database
