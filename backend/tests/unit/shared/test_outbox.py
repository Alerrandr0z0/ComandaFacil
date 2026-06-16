from __future__ import annotations

from unittest.mock import AsyncMock

from app.shared.outbox import OutboxEntry, OutboxWriter


class TestOutboxEntry:
    def test_outbox_entry_defaults(self) -> None:
        entry = OutboxEntry(
            aggregate_type="order",
            aggregate_id="42",
            event_type="order.canceled",
            payload='{"order_id": 42}',
        )
        assert entry.status == "pending"
        assert entry.retry_count == 0
        assert entry.created_at is not None

    def test_outbox_entry_repr(self) -> None:
        entry = OutboxEntry(
            aggregate_type="stock",
            aggregate_id="5",
            event_type="stock.adjusted",
            payload='{"item_id": 5}',
        )
        r = repr(entry)
        assert "OutboxEntry" in r
        assert "stock.adjusted" in r


class TestOutboxWriter:
    async def test_add_entry_creates_outbox_row(self) -> None:
        session = AsyncMock()
        writer = OutboxWriter(session)

        await writer.add_entry(
            aggregate_type="order",
            aggregate_id="100",
            event_type="order.created",
            payload='{"order_id": 100, "total": "39.90"}',
        )

        session.add.assert_called_once()
        entry: OutboxEntry = session.add.call_args[0][0]
        assert entry.aggregate_type == "order"
        assert entry.aggregate_id == "100"
        assert entry.event_type == "order.created"
        assert entry.payload == '{"order_id": 100, "total": "39.90"}'
        assert entry.status == "pending"
        assert entry.retry_count == 0

    async def test_add_entry_multiple_events(self) -> None:
        session = AsyncMock()
        writer = OutboxWriter(session)

        await writer.add_entry("order", "1", "order.created", "{}")
        await writer.add_entry("stock", "2", "stock.adjusted", "{}")

        assert session.add.call_count == 2
