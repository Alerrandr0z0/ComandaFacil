from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.dependencies import CurrentTenantId, DbSession, MongoDB, require_permission
from app.stock.application.commands import (
    CreateStockItemCommand,
    CreateStockItemHandler,
    StockService,
)
from app.stock.application.queries import (
    GetStockItemHandler,
    GetStockItemQuery,
    ListStockItemsHandler,
    ListStockItemsQuery,
)
from app.stock.domain.stock_item import StockItem
from app.stock.infrastructure.mongo_read_repository import MongoStockReadRepository
from app.stock.infrastructure.orm_models import StockTransactionORM
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyRecipeRepository,
    SQLAlchemyStockItemRepository,
)
from app.stock.infrastructure.stock_read_sync import StockReadModelSync

router = APIRouter(prefix="/stock", tags=["Stock"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────


class StockItemCreateSchema(BaseModel):
    id: int = Field(..., description="Unique stock item identifier")
    name: str = Field(..., max_length=255, description="Item name")
    category: str = Field(
        ..., max_length=100, description="Category (RAW_MATERIAL, BEVERAGE, etc.)"
    )
    current_quantity: float = Field(default=0.0, ge=0, description="Initial quantity")
    unit: str = Field(default="un", description="Measurement unit (g, kg, ml, l, un)")
    min_stock_level: float = Field(default=0.0, ge=0, description="Minimum stock alert level")

    model_config = ConfigDict(frozen=True)


class StockItemResponseSchema(BaseModel):
    id: int
    name: str
    category: str
    current_quantity_amount: float
    current_quantity_unit: str
    min_stock_level: float
    is_active: bool
    is_low_stock: bool

    model_config = ConfigDict(from_attributes=True, frozen=True)


class StockAddSchema(BaseModel):
    quantity: float = Field(..., gt=0, description="Positive quantity to add")
    reason: str = Field(default="", description="Reason for stock addition")
    reference_type: str | None = Field(default=None, description="Order type, etc.")
    reference_id: int | None = Field(default=None, description="Related entity ID")

    model_config = ConfigDict(frozen=True)


class StockDeductSchema(BaseModel):
    quantity: float = Field(..., gt=0, description="Positive quantity to deduct")
    reason: str = Field(default="", description="Reason for stock deduction")
    reference_type: str | None = Field(default=None, description="Order type, etc.")
    reference_id: int | None = Field(default=None, description="Related entity ID")

    model_config = ConfigDict(frozen=True)


class StockAdjustSchema(BaseModel):
    new_quantity: float = Field(..., ge=0, description="Absolute new quantity (physical count)")
    reason: str = Field(default="Inventory adjustment")

    model_config = ConfigDict(frozen=True)


class MinStockLevelSchema(BaseModel):
    min_stock_level: float = Field(..., ge=0, description="New minimum stock level")

    model_config = ConfigDict(frozen=True)


class StockMovementResponseSchema(BaseModel):
    id: int
    stock_item_id: int
    movement_type: str
    quantity_changed: float
    reason: str
    reference_type: str | None = None
    reference_id: int | None = None
    created_at: str

    model_config = ConfigDict(frozen=True)


# ─── REST Endpoints ───────────────────────────────────────────────────────────


@router.post(
    "/items",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new stock item",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def create_stock_item(
    schema: StockItemCreateSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> StockItemResponseSchema:
    repo = SQLAlchemyStockItemRepository(db)
    handler = CreateStockItemHandler(repo)
    command = CreateStockItemCommand(
        id=schema.id,
        tenant_id=tenant_id,
        name=schema.name,
        category=schema.category,
        current_quantity=Decimal(str(schema.current_quantity)),
        unit=schema.unit,
        min_stock_level=schema.min_stock_level,
    )
    item = await handler.handle(command)
    await db.commit()
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.get(
    "/items",
    response_model=list[StockItemResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all stock items",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def list_stock_items(
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
    low_stock_only: bool = Query(False, description="Filter low stock items only"),
) -> list[StockItemResponseSchema]:
    repo = MongoStockReadRepository(mongo)
    handler = ListStockItemsHandler(repo)
    items = await handler.handle(
        ListStockItemsQuery(tenant_id=tenant_id, low_stock_only=low_stock_only)
    )
    return [_stock_dict_to_response(i) for i in items]


@router.get(
    "/items/{item_id}",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a stock item by ID",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def get_stock_item(
    item_id: int,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> StockItemResponseSchema:
    repo = MongoStockReadRepository(mongo)
    handler = GetStockItemHandler(repo)
    item = await handler.handle(GetStockItemQuery(stock_item_id=item_id, tenant_id=tenant_id))
    if not item:
        raise HTTPException(status_code=404, detail=f"StockItem '{item_id}' não encontrado.")
    return _stock_dict_to_response(item)


@router.post(
    "/items/{item_id}/add",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Add stock to an item",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def add_stock(
    item_id: int,
    schema: StockAddSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> StockItemResponseSchema:
    item_repo = SQLAlchemyStockItemRepository(db)
    recipe_repo = SQLAlchemyRecipeRepository(db, item_repo)
    service = StockService(item_repo, recipe_repo)
    await service.add_input(item_id, Decimal(str(schema.quantity)), tenant_id)
    await db.commit()

    # Reload item for response
    item = await item_repo.find_by_id(item_id, tenant_id)
    if not item:
        raise HTTPException(status_code=404, detail="StockItem not found")
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.post(
    "/items/{item_id}/deduct",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Deduct stock from an item",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def deduct_stock(
    item_id: int,
    schema: StockDeductSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> StockItemResponseSchema:
    item_repo = SQLAlchemyStockItemRepository(db)
    recipe_repo = SQLAlchemyRecipeRepository(db, item_repo)
    service = StockService(item_repo, recipe_repo)

    try:
        await service.register_output(
            item_id, Decimal(str(schema.quantity)), tenant_id, schema.reason
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    await db.commit()

    item = await item_repo.find_by_id(item_id, tenant_id)
    if not item:
        raise HTTPException(status_code=404, detail="StockItem not found")
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.put(
    "/items/{item_id}/min-level",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Set minimum stock level",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def set_min_stock_level(
    item_id: int,
    schema: MinStockLevelSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> StockItemResponseSchema:
    repo = SQLAlchemyStockItemRepository(db)
    item = await repo.find_by_id(item_id, tenant_id)
    if not item:
        raise HTTPException(status_code=404, detail="StockItem not found")

    item.set_min_stock_level(schema.min_stock_level)
    await repo.save(item)
    await db.commit()
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.post(
    "/items/{item_id}/adjust",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Adjust stock to an absolute quantity",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def adjust_stock(
    item_id: int,
    schema: StockAdjustSchema,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> StockItemResponseSchema:
    item_repo = SQLAlchemyStockItemRepository(db)
    recipe_repo = SQLAlchemyRecipeRepository(db, item_repo)
    service = StockService(item_repo, recipe_repo)

    await service.adjust(item_id, Decimal(str(schema.new_quantity)), schema.reason, tenant_id)
    await db.commit()

    item = await item_repo.find_by_id(item_id, tenant_id)
    if not item:
        raise HTTPException(status_code=404, detail="StockItem not found")
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.get(
    "/items/{item_id}/movements",
    response_model=list[StockMovementResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="Get movement history for a stock item",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def get_stock_movements(
    item_id: int,
    db: DbSession,
    _tenant_id: CurrentTenantId,
) -> list[StockMovementResponseSchema]:
    # Query transactions
    stmt = (
        _from_val := select(StockTransactionORM)
        .where(StockTransactionORM.stock_item_id == item_id)
        .order_by(StockTransactionORM.occurred_at.desc())
    )
    res = await db.execute(stmt)
    txs = res.scalars().all()
    return [
        StockMovementResponseSchema(
            id=t.id,
            stock_item_id=t.stock_item_id,
            movement_type=t.transaction_type,
            quantity_changed=float(t.quantity_value),
            reason="",
            reference_type=None,
            reference_id=None,
            created_at=t.occurred_at.isoformat(),
        )
        for t in txs
    ]


# ─── Internal Helpers ─────────────────────────────────────────────────────────


def _item_to_response(item: StockItem) -> StockItemResponseSchema:
    bal = item.get_balance()
    return StockItemResponseSchema(
        id=item.id,
        name=item.name,
        category=item.category,
        current_quantity_amount=float(bal.value),
        current_quantity_unit=bal.unit,
        min_stock_level=item.min_stock_level,
        is_active=item.is_active,
        is_low_stock=item.is_low_stock,
    )


def _stock_dict_to_response(data: dict[str, object]) -> StockItemResponseSchema:
    sid = data["stock_item_id"]
    return StockItemResponseSchema(
        id=sid if isinstance(sid, int) else int(str(sid)),
        name=str(data["name"]),
        category=str(data["category"]),
        current_quantity_amount=float(str(data["current_quantity"])),
        current_quantity_unit=str(data["unit"]),
        min_stock_level=float(str(data["min_stock_level"])),
        is_active=bool(data["is_active"]),
        is_low_stock=bool(data["is_low_stock"]),
    )
