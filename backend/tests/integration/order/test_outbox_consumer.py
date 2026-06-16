from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.shared.base_orm import Base
from app.shared.outbox import OutboxConsumer, OutboxEntry, OutboxWriter

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def engine_and_factory() -> AsyncGenerator[
    tuple[Any, async_sessionmaker[AsyncSession]], None
]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield engine, factory
    await engine.dispose()


@pytest.fixture
def mock_mongo() -> tuple[AsyncMock, AsyncMock]:
    db = AsyncMock()
    col = AsyncMock()
    db.__getitem__.return_value = col
    return db, col


class TestOutboxConsumer:
    async def test_consumer_when_pending_entry_then_syncs_to_mongo(
        self,
        engine_and_factory: tuple[Any, async_sessionmaker[AsyncSession]],
        mock_mongo: tuple[AsyncMock, AsyncMock],
    ) -> None:
        _engine, factory = engine_and_factory
        mock_db, mock_col = mock_mongo

        # Arrange — write an outbox entry
        async with factory() as session:
            writer = OutboxWriter(session)
            await writer.add_entry(
                aggregate_type="order",
                aggregate_id="100",
                event_type="order.created",
                payload='{"order_id": "100", "tenant_id": "t1"}',
            )
            await session.commit()

        consumer = OutboxConsumer(
            session_factory=factory,
            mongo_db=mock_db,
            poll_interval=999,  # won't poll, we call _process_batch directly
        )

        # Act
        await consumer._process_batch()  # type: ignore

        # Assert — Mongo received the doc
        mock_col.replace_one.assert_awaited_once()
        call_args = mock_col.replace_one.call_args
        assert call_args is not None
        assert call_args[0][0] == {  # filter
            "aggregate_type": "order",
            "aggregate_id": "100",
            "event_type": "order.created",
        }
        assert call_args[0][1]["event_type"] == "order.created"
        assert call_args[1]["upsert"] is True

        # Assert — entry marked completed
        async with factory() as session:
            result = await session.execute(select(OutboxEntry))
            entry = result.scalar_one()
            assert entry.status == "completed"

    async def test_consumer_when_mongo_fails_then_retries_and_eventually_fails(
        self,
        engine_and_factory: tuple[Any, async_sessionmaker[AsyncSession]],
        mock_mongo: tuple[AsyncMock, AsyncMock],
    ) -> None:
        _engine, factory = engine_and_factory
        mock_db, mock_col = mock_mongo

        # Mongo always raises
        mock_col.replace_one.side_effect = ConnectionError("Mongo timeout")

        # Arrange — write an outbox entry
        async with factory() as session:
            writer = OutboxWriter(session)
            await writer.add_entry(
                aggregate_type="order",
                aggregate_id="200",
                event_type="order.canceled",
                payload='{"order_id": "200"}',
            )
            await session.commit()

        consumer = OutboxConsumer(
            session_factory=factory,
            mongo_db=mock_db,
            max_retries=2,
        )

        # Act — first attempt
        await consumer._process_batch()  # type: ignore

        async with factory() as session:
            entry = (await session.execute(select(OutboxEntry))).scalar_one()
            assert entry.status == "pending", "should still be pending after 1 retry"
            assert entry.retry_count == 1
            assert entry.error_message == "Mongo timeout"

        # Act — second attempt (hits max retries)
        await consumer._process_batch()  # type: ignore

        async with factory() as session:
            entry = (await session.execute(select(OutboxEntry))).scalar_one()
            assert entry.status == "failed", "should be failed after max retries"

    async def test_consumer_when_no_pending_entries_then_no_op(
        self,
        engine_and_factory: tuple[Any, async_sessionmaker[AsyncSession]],
        mock_mongo: tuple[AsyncMock, AsyncMock],
    ) -> None:
        _engine, factory = engine_and_factory
        mock_db, mock_col = mock_mongo

        consumer = OutboxConsumer(session_factory=factory, mongo_db=mock_db)

        await consumer._process_batch()  # type: ignore

        mock_col.replace_one.assert_not_called()
