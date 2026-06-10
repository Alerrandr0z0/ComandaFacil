from __future__ import annotations

import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.dependencies import CurrentTenantId, DbSession, MongoDB, require_permission
from app.menu.application.commands import (
    AddMenuItemCommand,
    AddMenuItemHandler,
    CreateCatalogItemCommand,
    CreateCatalogItemHandler,
    CreateMenuCommand,
    CreateMenuHandler,
    DeleteCatalogItemCommand,
    DeleteCatalogItemHandler,
    DeleteMenuCommand,
    DeleteMenuHandler,
    LinkMenuItemCommand,
    LinkMenuItemHandler,
    RemoveMenuItemCommand,
    RemoveMenuItemHandler,
    ToggleMenuCommand,
    ToggleMenuHandler,
    UpdateCatalogItemCommand,
    UpdateCatalogItemHandler,
)
from app.menu.application.queries import (
    GetMenuHandler,
    GetMenuQuery,
    ListMenuItemsHandler,
    ListMenuItemsQuery,
    ListMenusHandler,
    ListMenusQuery,
)
from app.menu.domain.menu import PreparationProfile
from app.menu.domain.price_list import PriceList, PriceListItem
from app.menu.infrastructure.mongo_read_repository import MongoMenuReadRepository
from app.menu.infrastructure.mongo_sync import MenuReadModelSync
from app.menu.infrastructure.orm_models import MenuItemORM, PriceListItemORM
from app.menu.infrastructure.repositories import (
    SQLAlchemyMenuItemRepository,
    SQLAlchemyMenuRepository,
    SQLAlchemyPriceListRepository,
)
from app.shared.money import Money

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
    price: Decimal | None = None
    image_url: str | None = None
    is_available: bool = True
    station_type: str = "GRILL"
    preparation_profile: str = "STANDARD"

    model_config = ConfigDict(frozen=True)


class MenuResponseSchema(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    price_list_id: int | None = None
    items: list[MenuItemSchema] = []

    model_config = ConfigDict(from_attributes=True, frozen=True)


class MenuItemAddSchema(BaseModel):
    id: int = Field(..., description="Unique item identifier")
    name: str = Field(..., max_length=255, description="Item name")
    description: str = Field(default="", description="Item description")
    category: str = Field(
        ..., max_length=100, description="Category name (e.g. 'Bebidas', 'Pratos')"
    )
    base_price: Decimal = Field(default=Decimal("0.00"), description="Base price fallback")
    station_type: str = Field(default="GRILL", description="Preparation station type")
    image_url: str | None = Field(default=None, description="Optional image URL")
    is_available: bool = Field(default=True, description="Availability flag")
    preparation_profile: str = Field(
        default="STANDARD", description="Preparation profile: STANDARD or NO_PREP"
    )

    model_config = ConfigDict(frozen=True)


class MenuToggleSchema(BaseModel):
    activate: bool = Field(..., description="True to activate, False to deactivate")

    model_config = ConfigDict(frozen=True)


class CatalogItemCreateSchema(BaseModel):
    id: int = Field(..., description="Unique item identifier")
    name: str = Field(..., max_length=255, description="Item name")
    description: str = Field(default="", description="Item description")
    category: str = Field(default="", max_length=100, description="Category name")
    base_price: Decimal = Field(default=Decimal("0.00"), description="Base price")
    station_type: str = Field(default="GRILL", description="Preparation station type")
    image_url: str | None = Field(default=None, description="Optional image URL")
    is_available: bool = Field(default=True, description="Availability flag")
    preparation_profile: str = Field(default="STANDARD", description="Preparation profile")

    model_config = ConfigDict(frozen=True)


class CatalogItemUpdateSchema(BaseModel):
    name: str = Field(..., max_length=255, description="Item name")
    description: str = Field(default="", description="Item description")
    category: str = Field(default="", max_length=100, description="Category name")
    base_price: Decimal = Field(..., ge=0, description="Base price")
    station_type: str = Field(default="GRILL", description="Preparation station type")
    image_url: str | None = Field(default=None, description="Optional image URL")
    is_available: bool = Field(default=True, description="Availability flag")

    model_config = ConfigDict(frozen=True)


# ─── REST Endpoints ───────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=MenuResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
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
    command = CreateMenuCommand(
        id=schema.id, tenant_id=tenant_id, name=schema.name, description=schema.description
    )
    menu = await handler.handle(command)
    await db.commit()

    menu_doc = await _resolve_menu_doc(db, menu)
    background_tasks.add_task(MenuReadModelSync(mongo).sync, menu_doc)

    return _menu_dict_to_response(menu_doc)


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
    "/items",
    response_model=list[MenuItemSchema],
    status_code=status.HTTP_200_OK,
    summary="List all menu items in the catalog",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def list_menu_items(
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> list[MenuItemSchema]:
    item_repo = SQLAlchemyMenuItemRepository(db)
    handler = ListMenuItemsHandler(item_repo)
    items = await handler.handle(ListMenuItemsQuery(tenant_id=tenant_id))
    return [
        MenuItemSchema(
            id=item.id,
            name=item.name,
            description=item.description,
            category=item.category_name,
            price=Decimal(str(item.base_price.amount)),
            image_url=item.image_url,
            is_available=item.is_available,
            station_type=item.station_type,
            preparation_profile=item.preparation_profile.value,
        )
        for item in items
    ]


@router.post(
    "/items",
    response_model=MenuItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new catalog item (standalone MenuItem)",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def create_catalog_item(
    schema: CatalogItemCreateSchema,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> MenuItemSchema:
    item_repo = SQLAlchemyMenuItemRepository(db)
    handler = CreateCatalogItemHandler(item_repo)
    command = CreateCatalogItemCommand(
        id=schema.id,
        tenant_id=tenant_id,
        name=schema.name,
        description=schema.description,
        category=schema.category,
        base_price=Money(schema.base_price),
        station_type=schema.station_type,
        image_url=schema.image_url,
        is_available=schema.is_available,
        preparation_profile=PreparationProfile(schema.preparation_profile),
    )
    item = await handler.handle(command)
    await db.commit()
    return MenuItemSchema(
        id=item.id,
        name=item.name,
        description=item.description,
        category=item.category_name,
        price=Decimal(str(item.base_price.amount)),
        image_url=item.image_url,
        is_available=item.is_available,
        station_type=item.station_type,
        preparation_profile=item.preparation_profile.value,
    )


@router.patch(
    "/items/{item_id}",
    response_model=MenuItemSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a catalog item (MenuItem)",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def update_catalog_item(
    item_id: int,
    schema: CatalogItemUpdateSchema,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> MenuItemSchema:
    item_repo = SQLAlchemyMenuItemRepository(db)
    handler = UpdateCatalogItemHandler(item_repo)
    command = UpdateCatalogItemCommand(
        item_id=item_id,
        tenant_id=tenant_id,
        name=schema.name,
        description=schema.description,
        category=schema.category,
        base_price=Money(schema.base_price),
        station_type=schema.station_type,
        image_url=schema.image_url,
        is_available=schema.is_available,
    )
    item = await handler.handle(command)
    await db.commit()
    return MenuItemSchema(
        id=item.id,
        name=item.name,
        description=item.description,
        category=item.category_name,
        price=Decimal(str(item.base_price.amount)),
        image_url=item.image_url,
        is_available=item.is_available,
        station_type=item.station_type,
        preparation_profile=item.preparation_profile.value,
    )


@router.delete(
    "/items/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a catalog item (MenuItem)",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def delete_catalog_item(
    item_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    item_repo = SQLAlchemyMenuItemRepository(db)
    handler = DeleteCatalogItemHandler(item_repo)
    command = DeleteCatalogItemCommand(item_id=item_id, tenant_id=tenant_id)
    await handler.handle(command)
    await db.commit()
    return {"detail": "Item do catálogo removido com sucesso."}


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
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
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
    item_repo = SQLAlchemyMenuItemRepository(db)
    handler = AddMenuItemHandler(repo, item_repo)
    command = AddMenuItemCommand(
        menu_id=menu_id,
        tenant_id=tenant_id,
        item_id=schema.id,
        name=schema.name,
        description=schema.description,
        category=schema.category,
        base_price=Money(schema.base_price),
        station_type=schema.station_type,
        image_url=schema.image_url,
        is_available=schema.is_available,
        preparation_profile=PreparationProfile(schema.preparation_profile),
    )
    item = await handler.handle(command)
    await db.commit()

    menu = await repo.find_by_id(menu_id, tenant_id)
    if menu:
        menu_doc = await _resolve_menu_doc(db, menu)
        background_tasks.add_task(MenuReadModelSync(mongo).sync, menu_doc)

    price_val = float(schema.base_price)
    if menu and menu.price_list_id:
        stmt = select(PriceListItemORM).where(
            PriceListItemORM.price_list_id == menu.price_list_id,
            PriceListItemORM.menu_item_id == item.id,
        )
        result = await db.execute(stmt)
        override = result.scalar_one_or_none()
        if override:
            price_val = float(override.price)

    return MenuItemSchema(
        id=item.id,
        name=item.name,
        description=item.description,
        category=item.category_name,
        price=Decimal(str(price_val)),
        image_url=item.image_url,
        is_available=item.is_available,
        station_type=item.station_type,
        preparation_profile=item.preparation_profile.value,
    )


@router.delete(
    "/{menu_id}/items/{item_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an item from a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
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
        menu_doc = await _resolve_menu_doc(db, menu)
        background_tasks.add_task(MenuReadModelSync(mongo).sync, menu_doc)

    return {"detail": "Item removido do cardápio com sucesso."}


@router.post(
    "/{menu_id}/link-item",
    response_model=MenuItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Link an existing catalog item to a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def link_menu_item(
    menu_id: int,
    schema: LinkMenuItemSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> MenuItemSchema:
    repo = SQLAlchemyMenuRepository(db)
    item_repo = SQLAlchemyMenuItemRepository(db)
    handler = LinkMenuItemHandler(repo, item_repo)
    command = LinkMenuItemCommand(
        menu_id=menu_id,
        tenant_id=tenant_id,
        item_id=schema.item_id,
        category=schema.category,
    )
    item = await handler.handle(command)
    await db.commit()

    menu = await repo.find_by_id(menu_id, tenant_id)
    if menu:
        menu_doc = await _resolve_menu_doc(db, menu)
        background_tasks.add_task(MenuReadModelSync(mongo).sync, menu_doc)

    return MenuItemSchema(
        id=item.id,
        name=item.name,
        description=item.description,
        category=schema.category,
        price=Decimal(str(item.base_price.amount)),
        image_url=item.image_url,
        is_available=item.is_available,
        station_type=item.station_type,
        preparation_profile=item.preparation_profile.value,
    )


class MenuItemPriceUpdateSchema(BaseModel):
    price: Decimal = Field(..., ge=0, description="New price of the menu item")

    model_config = ConfigDict(frozen=True)


class LinkMenuItemSchema(BaseModel):
    item_id: int = Field(..., description="ID of the existing menu item to link")
    category: str = Field(..., max_length=100, description="Category name to link into")

    model_config = ConfigDict(frozen=True)


@router.patch(
    "/{menu_id}/items/{item_id}/price",
    status_code=status.HTTP_200_OK,
    summary="Update the price of a menu item in a menu's price list",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def update_menu_item_price(
    menu_id: int,
    item_id: int,
    schema: MenuItemPriceUpdateSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    menu_repo = SQLAlchemyMenuRepository(db)
    price_list_repo = SQLAlchemyPriceListRepository(db)

    menu = await menu_repo.find_by_id(menu_id, tenant_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    # Get or create price list
    price_list = None
    if menu.price_list_id is not None:
        price_list = await price_list_repo.find_by_id(menu.price_list_id, tenant_id)

    if not price_list:
        pl_id = int(datetime.datetime.now(datetime.UTC).timestamp() * 1000) + int(item_id % 1000)
        price_list = PriceList(
            id=pl_id,
            tenant_id=tenant_id,
            menu_id=menu.id,
            name=f"Preços de {menu.name}",
            description=f"Lista de preços gerada automaticamente para o cardápio {menu.name}",
            is_active=True,
        )
        menu.price_list_id = pl_id
        await menu_repo.save(menu)

    # Find if item already exists in price list
    existing_item = next((pi for pi in price_list.items if pi.menu_item_id == item_id), None)
    if existing_item:
        existing_item.update_price(Money(schema.price))
    else:
        new_pi_id = (
            int(datetime.datetime.now(datetime.UTC).timestamp() * 1000) + int(item_id % 1000) + 1
        )
        new_item = PriceListItem(
            id=new_pi_id,
            price_list_id=price_list.id,
            menu_item_id=item_id,
            price=Money(schema.price),
        )
        price_list.add_item(new_item)

    await price_list_repo.save(price_list)
    await db.commit()

    # Sync menu read models to MongoDB
    updated_menu = await menu_repo.find_by_id(menu_id, tenant_id)
    if updated_menu:
        menu_doc = await _resolve_menu_doc(db, updated_menu)
        background_tasks.add_task(MenuReadModelSync(mongo).sync, menu_doc)

    return {"detail": "Preço do item atualizado com sucesso."}


@router.delete(
    "/{menu_id}/items/{item_id}/price",
    status_code=status.HTTP_200_OK,
    summary="Remove the special price override for a menu item",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def clear_menu_item_price(
    menu_id: int,
    item_id: int,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    menu_repo = SQLAlchemyMenuRepository(db)
    price_list_repo = SQLAlchemyPriceListRepository(db)

    menu = await menu_repo.find_by_id(menu_id, tenant_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    if menu.price_list_id is None:
        raise HTTPException(
            status_code=404, detail="Nenhum preço especial definido para este item."
        )

    price_list = await price_list_repo.find_by_id(menu.price_list_id, tenant_id)
    if not price_list:
        raise HTTPException(status_code=404, detail="Lista de preços não encontrada.")

    existing_item = next((pi for pi in price_list.items if pi.menu_item_id == item_id), None)
    if not existing_item:
        raise HTTPException(status_code=404, detail="Item não possui preço especial.")

    price_list.items.remove(existing_item)
    await price_list_repo.save(price_list)
    await db.commit()

    updated_menu = await menu_repo.find_by_id(menu_id, tenant_id)
    if updated_menu:
        menu_doc = await _resolve_menu_doc(db, updated_menu)
        background_tasks.add_task(MenuReadModelSync(mongo).sync, menu_doc)

    return {"detail": "Preço especial removido com sucesso."}


@router.patch(
    "/{menu_id}/toggle",
    response_model=MenuResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Activate or deactivate a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
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

    menu_doc = await _resolve_menu_doc(db, menu)
    background_tasks.add_task(MenuReadModelSync(mongo).sync, menu_doc)

    return _menu_to_response_doc(menu_doc)


@router.delete(
    "/{menu_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
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


# ─── Per-Menu Price List Management ──────────────────────────────────────────


@router.get(
    "/{menu_id}/price-lists",
    status_code=status.HTTP_200_OK,
    summary="List all PriceLists for a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def list_menu_price_lists(
    menu_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> list[dict[str, Any]]:
    repo = SQLAlchemyMenuRepository(db)
    menu_db = await repo.find_by_id(menu_id, tenant_id)
    if not menu_db:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    pl_repo = SQLAlchemyPriceListRepository(db)
    price_lists = await pl_repo.find_by_menu_id(menu_id, tenant_id)
    return [
        {
            "id": pl.id,
            "tenant_id": pl.tenant_id,
            "menu_id": pl.menu_id,
            "name": pl.name,
            "description": pl.description,
            "is_active": pl.is_active,
            "is_active_for_menu": pl.id == menu_db.price_list_id,
            "valid_from": pl.valid_from.isoformat(),
            "valid_until": pl.valid_until.isoformat() if pl.valid_until else None,
            "items": [
                {
                    "id": item.id,
                    "menu_item_id": item.menu_item_id,
                    "price": float(item.price.amount),
                }
                for item in pl.items
            ],
        }
        for pl in price_lists
    ]


@router.post(
    "/{menu_id}/price-lists",
    status_code=status.HTTP_201_CREATED,
    summary="Create a new PriceList for a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def create_menu_price_list(
    menu_id: int,
    schema: MenuPriceListCreateSchema,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, Any]:
    repo = SQLAlchemyMenuRepository(db)
    menu_db = await repo.find_by_id(menu_id, tenant_id)
    if not menu_db:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    pl_id = int(datetime.datetime.now(datetime.UTC).timestamp() * 1000) + hash(schema.name) % 10000
    price_list = PriceList(
        id=pl_id,
        tenant_id=tenant_id,
        menu_id=menu_id,
        name=schema.name,
        description=schema.description or "",
        is_active=True,
    )
    pl_repo = SQLAlchemyPriceListRepository(db)
    await pl_repo.save(price_list)
    await db.commit()

    return {
        "id": price_list.id,
        "tenant_id": price_list.tenant_id,
        "menu_id": price_list.menu_id,
        "name": price_list.name,
        "description": price_list.description,
        "is_active": price_list.is_active,
    }


@router.put(
    "/{menu_id}/activate-price-list/{price_list_id}",
    status_code=status.HTTP_200_OK,
    summary="Set a PriceList as the active one for a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def activate_menu_price_list(
    menu_id: int,
    price_list_id: int,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    menu_repo = SQLAlchemyMenuRepository(db)
    menu_db = await menu_repo.find_by_id(menu_id, tenant_id)
    if not menu_db:
        raise HTTPException(status_code=404, detail="Cardápio não encontrado.")

    pl_repo = SQLAlchemyPriceListRepository(db)
    price_list = await pl_repo.find_by_id(price_list_id, tenant_id)
    if not price_list:
        raise HTTPException(status_code=404, detail="Lista de preços não encontrada.")

    if price_list.menu_id != menu_id:
        raise HTTPException(
            status_code=400,
            detail="Esta lista de preços não pertence a este cardápio.",
        )

    menu_db.price_list_id = price_list_id
    await menu_repo.save(menu_db)
    await db.commit()

    menu_doc = await _resolve_menu_doc(db, menu_db)
    background_tasks.add_task(MenuReadModelSync(mongo).sync, menu_doc)

    return {"detail": "Lista de preços ativada com sucesso."}


class MenuPriceListCreateSchema(BaseModel):
    name: str = Field(..., max_length=255, description="Name for the new PriceList")
    description: str | None = Field(None, max_length=1000, description="Optional description")

    model_config = ConfigDict(frozen=True)


# ─── Internal Helpers ─────────────────────────────────────────────────────────


async def _resolve_menu_doc(db: DbSession, menu: Menu) -> dict[str, Any]:
    item_ids = []
    category_by_item_id = {}
    for category in menu.categories:
        for item in category.items:
            item_ids.append(item.menu_item_id)
            category_by_item_id[item.menu_item_id] = category.name

    items_data = []
    if item_ids:
        stmt = select(MenuItemORM).where(MenuItemORM.id.in_(item_ids))
        result = await db.execute(stmt)
        items_orm = result.scalars().all()

        prices_by_item_id = {}
        if menu.price_list_id:
            stmt = select(PriceListItemORM).where(
                PriceListItemORM.price_list_id == menu.price_list_id
            )
            result = await db.execute(stmt)
            price_items = result.scalars().all()
            prices_by_item_id = {pi.menu_item_id: pi.price for pi in price_items}

        for item_orm in items_orm:
            override_price = prices_by_item_id.get(item_orm.id)
            final_price = override_price if override_price is not None else item_orm.base_price
            items_data.append(
                {
                    "id": item_orm.id,
                    "name": item_orm.name,
                    "description": item_orm.description,
                    "price": float(final_price),
                    "category": category_by_item_id.get(item_orm.id, item_orm.category_name),
                    "image_url": item_orm.image_url,
                    "is_available": item_orm.is_available,
                    "station_type": item_orm.station_type,
                    "preparation_profile": item_orm.preparation_profile,
                }
            )

    return {
        "menu_id": menu.id,
        "tenant_id": menu.tenant_id,
        "name": menu.name,
        "description": menu.description,
        "is_active": menu.is_active,
        "price_list_id": menu.price_list_id,
        "items": items_data,
    }


def _menu_to_response_doc(doc: dict[str, Any]) -> MenuResponseSchema:
    return _menu_dict_to_response(doc)


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
        price_list_id=data.get("price_list_id"),  # type: ignore[arg-type]
        items=[
            MenuItemSchema(
                id=int(str(item["id"])),
                name=str(item["name"]),
                description=str(item.get("description", "")),
                category=str(item["category"]),
                price=Decimal(str(item["price"])) if item.get("price") is not None else None,
                image_url=str(item["image_url"]) if item.get("image_url") else None,
                is_available=bool(item["is_available"]),
                station_type=str(item.get("station_type", "GRILL")),
                preparation_profile=str(item.get("preparation_profile", "STANDARD")),
            )
            for item in items_raw
        ],
    )
