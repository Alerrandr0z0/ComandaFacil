from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.dependencies import CurrentTenantId, DbSession, MongoDB
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
from app.menu.infrastructure.mongo_read_repository import MongoMenuReadRepository
from app.menu.infrastructure.mongo_sync import MenuReadModelSync
from app.menu.infrastructure.repositories import SQLAlchemyMenuRepository

if TYPE_CHECKING:
    from app.menu.domain.menu import Menu

router = APIRouter(prefix="/menu", tags=["Menu"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────


class MenuCreateSchema(BaseModel):
    id: int = Field(..., description="Unique menu identifier")
    name: str = Field(..., max_length=255, description="Menu display name")
    description: str = Field(default="", description="Optional description")

    model_config = ConfigDict(frozen=True)


class MenuItemSchema(BaseModel):
    id: int
    name: str
    description: str
    category: str
    image_url: str | None = None
    is_available: bool = True

    model_config = ConfigDict(frozen=True)


class MenuResponseSchema(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    items: list[MenuItemSchema] = []

    model_config = ConfigDict(from_attributes=True, frozen=True)


class MenuItemAddSchema(BaseModel):
    id: int = Field(..., description="Unique item identifier")
    name: str = Field(..., max_length=255, description="Item name")
    description: str = Field(default="", description="Item description")
    category: str = Field(
        ..., max_length=100, description="Category name (e.g. 'Bebidas', 'Pratos')"
    )
    image_url: str | None = Field(default=None, description="Optional image URL")
    is_available: bool = Field(default=True, description="Availability flag")

    model_config = ConfigDict(frozen=True)


class MenuToggleSchema(BaseModel):
    activate: bool = Field(..., description="True to activate, False to deactivate")

    model_config = ConfigDict(frozen=True)


# ─── REST Endpoints ───────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=MenuResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Menu",
)
async def create_menu(
    schema: MenuCreateSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> MenuResponseSchema:
    repo = SQLAlchemyMenuRepository(db)
    handler = CreateMenuHandler(repo)
    command = CreateMenuCommand(id=schema.id, tenant_id=tenant_id, name=schema.name, description=schema.description)
    menu = await handler.handle(command)
    await db.commit()

    background_tasks.add_task(MenuReadModelSync(mongo).sync, menu)

    return _menu_to_response(menu)


@router.get(
    "",
    response_model=list[MenuResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all Menus",
)
async def list_menus(
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> list[MenuResponseSchema]:
    repo = MongoMenuReadRepository(mongo)
    handler = ListMenusHandler(repo)
    menus = await handler.handle(ListMenusQuery(tenant_id=tenant_id))
    return [_menu_dict_to_response(m) for m in menus]


@router.get(
    "/{menu_id}",
    response_model=MenuResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a Menu by ID",
)
async def get_menu(
    menu_id: int,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> MenuResponseSchema:
    repo = MongoMenuReadRepository(mongo)
    handler = GetMenuHandler(repo)
    menu = await handler.handle(GetMenuQuery(menu_id=menu_id, tenant_id=tenant_id))
    if not menu:
        raise HTTPException(status_code=404, detail=f"Cardápio '{menu_id}' não encontrado.")
    return _menu_dict_to_response(menu)


@router.post(
    "/{menu_id}/items",
    response_model=MenuItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to a Menu",
)
async def add_menu_item(
    menu_id: int,
    schema: MenuItemAddSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> MenuItemSchema:
    repo = SQLAlchemyMenuRepository(db)
    handler = AddMenuItemHandler(repo)
    command = AddMenuItemCommand(
        menu_id=menu_id,
        tenant_id=tenant_id,
        item_id=schema.id,
        name=schema.name,
        description=schema.description,
        category=schema.category,
        image_url=schema.image_url,
        is_available=schema.is_available,
    )
    item = await handler.handle(command)
    await db.commit()

    menu = await repo.find_by_id(menu_id, tenant_id)
    if menu:
        background_tasks.add_task(MenuReadModelSync(mongo).sync, menu)

    return MenuItemSchema(
        id=item.id,
        name=item.name,
        description=item.description,
        category=str(item.category),
        image_url=item.image_url,
        is_available=item.is_available,
    )


@router.delete(
    "/{menu_id}/items/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an item from a Menu",
)
async def remove_menu_item(
    menu_id: int,
    item_id: int,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    repo = SQLAlchemyMenuRepository(db)
    handler = RemoveMenuItemHandler(repo)
    command = RemoveMenuItemCommand(menu_id=menu_id, tenant_id=tenant_id, item_id=item_id)
    await handler.handle(command)
    await db.commit()

    menu = await repo.find_by_id(menu_id, tenant_id)
    if menu:
        background_tasks.add_task(MenuReadModelSync(mongo).sync, menu)

    return {"detail": "Item removido do cardápio com sucesso."}


@router.patch(
    "/{menu_id}/toggle",
    response_model=MenuResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Activate or deactivate a Menu",
)
async def toggle_menu(
    menu_id: int,
    schema: MenuToggleSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> MenuResponseSchema:
    repo = SQLAlchemyMenuRepository(db)
    handler = ToggleMenuHandler(repo)
    command = ToggleMenuCommand(menu_id=menu_id, tenant_id=tenant_id, activate=schema.activate)
    menu = await handler.handle(command)
    await db.commit()

    background_tasks.add_task(MenuReadModelSync(mongo).sync, menu)

    return _menu_to_response(menu)


@router.delete(
    "/{menu_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a Menu",
)
async def delete_menu(
    menu_id: int,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    repo = SQLAlchemyMenuRepository(db)
    handler = DeleteMenuHandler(repo)
    command = DeleteMenuCommand(menu_id=menu_id, tenant_id=tenant_id)
    await handler.handle(command)
    await db.commit()

    background_tasks.add_task(MenuReadModelSync(mongo).remove, menu_id)

    return {"detail": "Cardápio removido com sucesso."}


# ─── Internal Helpers ─────────────────────────────────────────────────────────


def _menu_to_response(menu: object) -> MenuResponseSchema:
    m: Menu = menu  # type: ignore[no-redef]
    return MenuResponseSchema(
        id=m.id,
        name=m.name,
        description=m.description,
        is_active=m.is_active,
        items=[
            MenuItemSchema(
                id=item.id,
                name=item.name,
                description=item.description,
                category=str(item.category),
                image_url=item.image_url,
                is_available=item.is_available,
            )
            for item in m.items
        ],
    )


def _menu_dict_to_response(data: dict[str, object]) -> MenuResponseSchema:
    items_raw = data.get("items", [])
    assert isinstance(items_raw, list)
    mid = data["menu_id"]
    mid_int = mid if isinstance(mid, int) else int(str(mid))
    return MenuResponseSchema(
        id=mid_int,
        name=str(data["name"]),
        description=str(data.get("description", "")),
        is_active=bool(data["is_active"]),
        items=[
            MenuItemSchema(
                id=int(str(item["id"])),
                name=str(item["name"]),
                description=str(item.get("description", "")),
                category=str(item["category"]),
                image_url=str(item["image_url"]) if item.get("image_url") else None,
                is_available=bool(item["is_available"]),
            )
            for item in items_raw
        ],
    )
