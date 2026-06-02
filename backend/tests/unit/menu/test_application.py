from __future__ import annotations

import pytest

from app.menu.application.commands import (
    AddMenuItemCommand,
    AddMenuItemHandler,
    CreateMenuCommand,
    CreateMenuHandler,
    DeleteMenuCommand,
    DeleteMenuHandler,
    RemoveMenuItemCommand,
    RemoveMenuItemHandler,
    ToggleMenuCommand,
    ToggleMenuHandler,
)
from app.menu.application.queries import (
    GetMenuHandler,
    GetMenuQuery,
    ListMenusHandler,
    ListMenusQuery,
)
from app.menu.domain.category import Category
from app.menu.domain.menu import Menu, MenuItem, MenuRepository
from app.shared.exceptions import ConflictError, NotFoundError


class InMemoryMenuRepository(MenuRepository):
    def __init__(self) -> None:
        self._menus: dict[int, Menu] = {}

    async def find_by_id(self, id: int, tenant_id: str = "") -> Menu | None:
        return self._menus.get(id)

    async def find_all(self, tenant_id: str = "") -> list[Menu]:
        return list(self._menus.values())

    async def save(self, menu: Menu) -> None:
        self._menus[menu.id] = menu

    async def delete(self, id: int, tenant_id: str = "") -> None:
        self._menus.pop(id, None)


@pytest.fixture
def menu_repo() -> InMemoryMenuRepository:
    return InMemoryMenuRepository()


@pytest.mark.unit
async def test_create_menu_success(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    handler = CreateMenuHandler(menu_repo)
    command = CreateMenuCommand(id=1, tenant_id="test", name="Almoço", description="Cardápio do almoço")

    # Act
    menu = await handler.handle(command)

    # Assert
    assert menu.id == 1
    assert menu.name == "Almoço"
    assert menu.description == "Cardápio do almoço"
    assert menu.is_active is True

    saved = await menu_repo.find_by_id(1)
    assert saved is not None
    assert saved.name == "Almoço"


@pytest.mark.unit
async def test_create_menu_duplicate_id(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    handler = CreateMenuHandler(menu_repo)
    existing = Menu(id=1, tenant_id="test", name="Almoço", description="", is_active=True)
    await menu_repo.save(existing)
    command = CreateMenuCommand(id=1, tenant_id="test", name="Jantar", description="")

    # Act & Assert
    with pytest.raises(ConflictError, match="Cardápio com id 1 já existe"):
        await handler.handle(command)


@pytest.mark.unit
async def test_add_menu_item_success(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    menu = Menu(id=1, tenant_id="test", name="Almoço")
    await menu_repo.save(menu)
    handler = AddMenuItemHandler(menu_repo)
    command = AddMenuItemCommand(
        menu_id=1,
        tenant_id="test",
        item_id=10,
        name="Feijoada",
        description="Feijoada completa",
        category="Pratos",
    )

    # Act
    item = await handler.handle(command)

    # Assert
    assert item.id == 10
    assert item.name == "Feijoada"
    assert str(item.category) == "Pratos"

    saved = await menu_repo.find_by_id(1)
    assert saved is not None
    assert len(saved.items) == 1
    assert saved.items[0].name == "Feijoada"


@pytest.mark.unit
async def test_add_menu_item_nonexistent_menu(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    handler = AddMenuItemHandler(menu_repo)
    command = AddMenuItemCommand(
        menu_id=99,
        tenant_id="test",
        item_id=1,
        name="Pizza",
        description="Pizza",
        category="Pizzas",
    )

    # Act & Assert
    with pytest.raises(NotFoundError, match="Cardápio '99' não encontrado"):
        await handler.handle(command)


@pytest.mark.unit
async def test_remove_menu_item_success(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    menu = Menu(id=1, tenant_id="test", name="Almoço")
    item = MenuItem(id=10, name="Feijoada", description="", category=Category("Pratos"))
    menu.add_item(item)
    await menu_repo.save(menu)
    handler = RemoveMenuItemHandler(menu_repo)
    command = RemoveMenuItemCommand(menu_id=1, tenant_id="test", item_id=10)

    # Act
    await handler.handle(command)

    # Assert
    saved = await menu_repo.find_by_id(1)
    assert saved is not None
    assert len(saved.items) == 0


@pytest.mark.unit
async def test_remove_menu_item_nonexistent_menu(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    handler = RemoveMenuItemHandler(menu_repo)
    command = RemoveMenuItemCommand(menu_id=99, tenant_id="test", item_id=1)

    # Act & Assert
    with pytest.raises(NotFoundError, match="Cardápio '99' não encontrado"):
        await handler.handle(command)


@pytest.mark.unit
async def test_toggle_menu_activate(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    menu = Menu(id=1, tenant_id="test", name="Almoço", is_active=False)
    await menu_repo.save(menu)
    handler = ToggleMenuHandler(menu_repo)
    command = ToggleMenuCommand(menu_id=1, tenant_id="test", activate=True)


    # Act
    result = await handler.handle(command)

    # Assert
    assert result.is_active is True

    saved = await menu_repo.find_by_id(1)
    assert saved is not None
    assert saved.is_active is True


@pytest.mark.unit
async def test_toggle_menu_deactivate(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    menu = Menu(id=1, tenant_id="test", name="Almoço", is_active=True)
    await menu_repo.save(menu)
    handler = ToggleMenuHandler(menu_repo)
    command = ToggleMenuCommand(menu_id=1, tenant_id="test", activate=False)

    # Act
    result = await handler.handle(command)

    # Assert
    assert result.is_active is False


@pytest.mark.unit
async def test_toggle_menu_nonexistent(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    handler = ToggleMenuHandler(menu_repo)
    command = ToggleMenuCommand(menu_id=99, tenant_id="test", activate=True)

    # Act & Assert
    with pytest.raises(NotFoundError, match="Cardápio '99' não encontrado"):
        await handler.handle(command)


@pytest.mark.unit
async def test_delete_menu_success(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    menu = Menu(id=1, tenant_id="test", name="Almoço")
    await menu_repo.save(menu)
    handler = DeleteMenuHandler(menu_repo)
    command = DeleteMenuCommand(menu_id=1, tenant_id="test")

    # Act
    await handler.handle(command)

    # Assert
    assert await menu_repo.find_by_id(1) is None


@pytest.mark.unit
async def test_delete_menu_nonexistent(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    handler = DeleteMenuHandler(menu_repo)
    command = DeleteMenuCommand(menu_id=99, tenant_id="test")

    # Act & Assert
    with pytest.raises(NotFoundError, match="Cardápio '99' não encontrado"):
        await handler.handle(command)


@pytest.mark.unit
async def test_get_menu_query(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    menu = Menu(id=1, tenant_id="test", name="Almoço")
    await menu_repo.save(menu)
    handler = GetMenuHandler(menu_repo)
    query = GetMenuQuery(menu_id=1, tenant_id="test")

    # Act
    result = await handler.handle(query)

    # Assert
    assert result is not None
    assert result.id == 1
    assert result.name == "Almoço"


@pytest.mark.unit
async def test_get_menu_query_not_found(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    handler = GetMenuHandler(menu_repo)
    query = GetMenuQuery(menu_id=99, tenant_id="test")

    # Act
    result = await handler.handle(query)

    # Assert
    assert result is None


@pytest.mark.unit
async def test_list_menus_query(menu_repo: InMemoryMenuRepository) -> None:
    # Arrange
    await menu_repo.save(Menu(id=1, tenant_id="test", name="Almoço"))
    await menu_repo.save(Menu(id=2, tenant_id="test", name="Jantar"))
    handler = ListMenusHandler(menu_repo)
    query = ListMenusQuery(tenant_id="test")

    # Act
    results = await handler.handle(query)

    # Assert
    assert len(results) == 2
    assert results[0].name == "Almoço"
    assert results[1].name == "Jantar"
