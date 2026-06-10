from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.dependencies import CurrentTenantId, DbSession, require_permission
from app.menu.application.commands import (
    AddPriceListItemCommand,
    AddPriceListItemHandler,
    AssociatePriceListToMenuCommand,
    AssociatePriceListToMenuHandler,
    CreatePriceListCommand,
    CreatePriceListHandler,
    DeletePriceListCommand,
    DeletePriceListHandler,
    RemovePriceListItemCommand,
    RemovePriceListItemHandler,
    UpdatePriceListCommand,
    UpdatePriceListHandler,
)
from app.menu.application.queries import (
    GetPriceListHandler,
    GetPriceListQuery,
    ListPriceListsHandler,
    ListPriceListsQuery,
)
from app.menu.domain.price_list import PriceList as PriceListDomain
from app.menu.infrastructure.repositories import (
    SQLAlchemyMenuRepository,
    SQLAlchemyPriceListRepository,
)
from app.shared.money import Money

router = APIRouter(prefix="/menu/price-lists", tags=["Menu / Price Lists"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────


class PriceListCreateSchema(BaseModel):
    id: int = Field(..., description="Unique price list identifier")
    menu_id: int = Field(..., description="Menu to which this price list belongs")
    name: str = Field(..., max_length=255, description="Price list display name")
    description: str = Field(default="", description="Optional description")
    is_active: bool = Field(default=True, description="Whether this price list is active")

    model_config = ConfigDict(frozen=True)


class PriceListUpdateSchema(BaseModel):
    name: str = Field(..., max_length=255, description="Price list display name")
    description: str = Field(default="", description="Optional description")
    is_active: bool = Field(..., description="Whether this price list is active")

    model_config = ConfigDict(frozen=True)


class PriceListItemAddSchema(BaseModel):
    item_id: int = Field(..., description="Price list item identifier")
    menu_item_id: int = Field(..., description="MenuItem to price")
    price: Decimal = Field(..., ge=0, description="Override price")

    model_config = ConfigDict(frozen=True)


class PriceListAssociateSchema(BaseModel):
    price_list_id: int | None = Field(
        None, description="Price list ID to associate, or null to disassociate"
    )

    model_config = ConfigDict(frozen=True)


class PriceListItemResponseSchema(BaseModel):
    id: int
    menu_item_id: int
    price: float

    model_config = ConfigDict(frozen=True)


class PriceListResponseSchema(BaseModel):
    id: int
    name: str
    description: str
    is_active: bool
    items: list[PriceListItemResponseSchema] = []

    model_config = ConfigDict(frozen=True)


# ─── Helper ───────────────────────────────────────────────────────────────────


def _pl_to_response(pl: Any) -> PriceListResponseSchema:
    if isinstance(pl, PriceListDomain):
        pid = pl.id
        name = pl.name
        desc = pl.description
        active = pl.is_active
        items_raw = pl.items
    elif isinstance(pl, dict):
        pid = pl["id"]
        name = pl["name"]
        desc = pl.get("description", "")
        active = pl.get("is_active", True)
        items_raw = pl.get("items", [])
    else:
        pid = pl.id
        name = pl.name
        desc = getattr(pl, "description", "")
        active = getattr(pl, "is_active", True)
        items_raw = getattr(pl, "items", [])

    items = []
    for i in items_raw:
        if hasattr(i.price, "amount"):
            price_val = float(str(i.price.amount))
        elif isinstance(i.price, (int, float)):
            price_val = float(i.price)
        else:
            price_val = float(str(i.price))
        items.append(
            PriceListItemResponseSchema(
                id=i.id,
                menu_item_id=i.menu_item_id,
                price=price_val,
            )
        )
    return PriceListResponseSchema(
        id=pid,
        name=name,
        description=desc,
        is_active=active,
        items=items,
    )


# ─── Endpoints ────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=PriceListResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Price List",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def create_price_list(
    schema: PriceListCreateSchema,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> PriceListResponseSchema:
    repo = SQLAlchemyPriceListRepository(db)
    handler = CreatePriceListHandler(repo)
    command = CreatePriceListCommand(
        id=schema.id,
        tenant_id=tenant_id,
        menu_id=schema.menu_id,
        name=schema.name,
        description=schema.description,
        is_active=schema.is_active,
    )
    pl = await handler.handle(command)
    await db.commit()
    return _pl_to_response(pl)


@router.get(
    "",
    response_model=list[PriceListResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all Price Lists",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def list_price_lists(
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> list[PriceListResponseSchema]:
    repo = SQLAlchemyPriceListRepository(db)
    handler = ListPriceListsHandler(repo)
    price_lists = await handler.handle(ListPriceListsQuery(tenant_id=tenant_id))
    return [_pl_to_response(pl) for pl in price_lists]


@router.get(
    "/{price_list_id}",
    response_model=PriceListResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a Price List by ID",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def get_price_list(
    price_list_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> PriceListResponseSchema:
    repo = SQLAlchemyPriceListRepository(db)
    handler = GetPriceListHandler(repo)
    pl = await handler.handle(GetPriceListQuery(price_list_id=price_list_id, tenant_id=tenant_id))
    if not pl:
        raise HTTPException(status_code=404, detail=f"Price list '{price_list_id}' não encontrada.")
    return _pl_to_response(pl)


@router.put(
    "/{price_list_id}",
    response_model=PriceListResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Update a Price List metadata",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def update_price_list(
    price_list_id: int,
    schema: PriceListUpdateSchema,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> PriceListResponseSchema:
    repo = SQLAlchemyPriceListRepository(db)
    handler = UpdatePriceListHandler(repo)
    command = UpdatePriceListCommand(
        price_list_id=price_list_id,
        tenant_id=tenant_id,
        name=schema.name,
        description=schema.description,
        is_active=schema.is_active,
        valid_from=None,
        valid_until=None,
    )
    pl = await handler.handle(command)
    await db.commit()
    return _pl_to_response(pl)


@router.delete(
    "/{price_list_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a Price List",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def delete_price_list(
    price_list_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    repo = SQLAlchemyPriceListRepository(db)
    handler = DeletePriceListHandler(repo)
    command = DeletePriceListCommand(price_list_id=price_list_id, tenant_id=tenant_id)
    await handler.handle(command)
    await db.commit()
    return {"detail": "Lista de preços removida com sucesso."}


@router.post(
    "/{price_list_id}/items",
    response_model=PriceListItemResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update an item price in a Price List",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def add_price_list_item(
    price_list_id: int,
    schema: PriceListItemAddSchema,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> PriceListItemResponseSchema:
    repo = SQLAlchemyPriceListRepository(db)
    handler = AddPriceListItemHandler(repo)
    command = AddPriceListItemCommand(
        price_list_id=price_list_id,
        tenant_id=tenant_id,
        item_id=schema.item_id,
        menu_item_id=schema.menu_item_id,
        price=Money(schema.price),
    )
    item = await handler.handle(command)
    await db.commit()
    return PriceListItemResponseSchema(
        id=item.id,
        menu_item_id=item.menu_item_id,
        price=float(str(item.price.amount)),
    )


@router.delete(
    "/{price_list_id}/items/{menu_item_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove an item from a Price List",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def remove_price_list_item(
    price_list_id: int,
    menu_item_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    repo = SQLAlchemyPriceListRepository(db)
    handler = RemovePriceListItemHandler(repo)
    command = RemovePriceListItemCommand(
        price_list_id=price_list_id,
        tenant_id=tenant_id,
        menu_item_id=menu_item_id,
    )
    await handler.handle(command)
    await db.commit()
    return {"detail": "Item removido da lista de preços."}


@router.put(
    "/{price_list_id}/associate/{menu_id}",
    status_code=status.HTTP_200_OK,
    summary="Associate a Price List with a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def associate_price_list_to_menu(
    price_list_id: int,
    menu_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    menu_repo = SQLAlchemyMenuRepository(db)
    handler = AssociatePriceListToMenuHandler(menu_repo)
    command = AssociatePriceListToMenuCommand(
        menu_id=menu_id,
        tenant_id=tenant_id,
        price_list_id=price_list_id,
    )
    await handler.handle(command)
    await db.commit()
    return {"detail": "Lista de preços associada ao cardápio."}


@router.delete(
    "/{price_list_id}/associate/{menu_id}",
    status_code=status.HTTP_200_OK,
    summary="Disassociate a Price List from a Menu",
    dependencies=[Depends(require_permission("MANAGE_MENU"))],
)
async def disassociate_price_list_from_menu(
    _price_list_id: int,
    menu_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    menu_repo = SQLAlchemyMenuRepository(db)
    handler = AssociatePriceListToMenuHandler(menu_repo)
    command = AssociatePriceListToMenuCommand(
        menu_id=menu_id,
        tenant_id=tenant_id,
        price_list_id=None,
    )
    await handler.handle(command)
    await db.commit()
    return {"detail": "Lista de preços desassociada do cardápio."}
