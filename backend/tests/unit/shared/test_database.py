import pytest

from app.shared import database


@pytest.mark.asyncio
async def test_get_async_session_raises_runtime_error() -> None:
    # Ensure session_factory is None
    database.session_factory = None
    with pytest.raises(RuntimeError, match="PostgreSQL not initialized"):
        async for _ in database.get_async_session():
            pass


def test_get_mongo_db_raises_runtime_error() -> None:
    # Ensure _mongo_database is None
    database._mongo_database = None  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(RuntimeError, match="MongoDB not initialized"):
        database.get_mongo_db()
