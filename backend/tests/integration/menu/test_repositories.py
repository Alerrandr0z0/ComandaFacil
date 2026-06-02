from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.menu.domain.category import Category
from app.menu.domain.menu import Menu, MenuItem
from app.menu.domain.price_list import PriceList, PriceListItem
from app.menu.infrastructure.repositories import (
    SQLAlchemyMenuRepository,
    SQLAlchemyPriceListRepository,
)
from app.shared.base_orm import Base
from app.shared.money import Money

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async session fixture utilizing in-memory SQLite for extremely fast integration tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    # Create all tables in the SQLite database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest.mark.asyncio
async def test_menu_repository_lifecycle(db_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyMenuRepository(db_session)

    # 1. Save new menu
    menu = Menu(id=1, tenant_id="test", name="Almoço", description="Cardápio de almoço", is_active=True)
    item = MenuItem(
        id=10,
        name="Feijoada",
        description="Feijoada tradicional",
        category=Category("Pratos"),
        image_url="http://example.com/feijoada.jpg",
        is_available=True,
    )
    menu.add_item(item)
    await repo.save(menu)
    await db_session.commit()

    # 2. Retrieve menu and verify mapping
    retrieved = await repo.find_by_id(1, "test")
    assert retrieved is not None
    assert retrieved.id == 1
    assert retrieved.name == "Almoço"
    assert retrieved.description == "Cardápio de almoço"
    assert retrieved.is_active is True
    assert len(retrieved.items) == 1
    assert retrieved.items[0].id == 10
    assert retrieved.items[0].name == "Feijoada"
    assert str(retrieved.items[0].category) == "Pratos"
    assert retrieved.items[0].image_url == "http://example.com/feijoada.jpg"

    # 3. Update menu (add another item, modify status)
    retrieved.name = "Almoço Executivo"
    retrieved.deactivate()
    new_item = MenuItem(
        id=11,
        name="Guaraná",
        description="Lata 350ml",
        category=Category("Bebidas"),
        is_available=True,
    )
    retrieved.add_item(new_item)
    await repo.save(retrieved)
    await db_session.commit()

    # 4. Verify updates
    updated = await repo.find_by_id(1, "test")
    assert updated is not None
    assert updated.name == "Almoço Executivo"
    assert updated.is_active is False
    assert len(updated.items) == 2
    assert any(x.id == 11 and x.name == "Guaraná" for x in updated.items)

    # 5. Delete menu and verify cascade deletion
    await repo.delete(1, "test")
    await db_session.commit()

    deleted = await repo.find_by_id(1, "test")
    assert deleted is None


@pytest.mark.asyncio
async def test_price_list_repository_lifecycle(db_session: AsyncSession) -> None:
    # Arrange
    repo = SQLAlchemyPriceListRepository(db_session)
    valid_from = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
    valid_until = datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=7)

    # 1. Save new PriceList
    pl = PriceList(
        id=1,
        tenant_id="test",
        name="Preços Padrão",
        description="Tabela regular",
        is_active=True,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    item = PriceListItem(id=100, price_list_id=1, menu_item_id=10, price=Money.from_float(39.90))
    pl.add_item(item)
    await repo.save(pl)
    await db_session.commit()

    # 2. Find by id
    retrieved = await repo.find_by_id(1, "test")
    assert retrieved is not None
    assert retrieved.id == 1
    assert retrieved.name == "Preços Padrão"
    assert retrieved.is_active is True
    assert len(retrieved.items) == 1
    assert retrieved.items[0].menu_item_id == 10
    assert retrieved.items[0].price == Money.from_float(39.90)

    # 3. Find active price lists
    active_lists = await repo.find_active("test")
    assert len(active_lists) == 1
    assert active_lists[0].id == 1

    # 4. Update PriceList items
    retrieved.deactivate()
    retrieved.items[0].update_price(Money.from_float(42.50))
    new_price = PriceListItem(
        id=101, price_list_id=1, menu_item_id=11, price=Money.from_float(7.90)
    )
    retrieved.add_item(new_price)
    await repo.save(retrieved)
    await db_session.commit()

    # 5. Verify update
    updated = await repo.find_by_id(1, "test")
    assert updated is not None
    assert updated.is_active is False
    assert len(updated.items) == 2
    assert updated.get_price(10) == Money.from_float(42.50)
    assert updated.get_price(11) == Money.from_float(7.90)
