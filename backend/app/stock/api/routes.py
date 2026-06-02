from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.dependencies import CurrentTenantId, DbSession, MongoDB
from app.stock.application.commands import (
    AddStockCommand,
    AddStockHandler,
    AdjustStockCommand,
    AdjustStockHandler,
    CreateStockItemCommand,
    CreateStockItemHandler,
    DeductStockCommand,
    DeductStockHandler,
    SetMinStockLevelCommand,
    SetMinStockLevelHandler,
)
from app.stock.application.queries import (
    GetStockItemHandler,
    GetStockItemQuery,
    ListStockItemsHandler,
    ListStockItemsQuery,
)
from app.stock.domain.stock_item import StockItem
from app.stock.infrastructure.mongo_read_repository import MongoStockReadRepository
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyStockItemRepository,
    SQLAlchemyStockMovementRepository,
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
        current_quantity=schema.current_quantity,
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
    movement_repo = SQLAlchemyStockMovementRepository(db)
    handler = AddStockHandler(item_repo, movement_repo)
    item = await handler.handle(
        AddStockCommand(
            stock_item_id=item_id,
            tenant_id=tenant_id,
            quantity=schema.quantity,
            reason=schema.reason,
            reference_type=schema.reference_type,
            reference_id=schema.reference_id,
        )
    )
    await db.commit()
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.post(
    "/items/{item_id}/deduct",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Deduct stock from an item",
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
    movement_repo = SQLAlchemyStockMovementRepository(db)
    handler = DeductStockHandler(item_repo, movement_repo)
    try:
        item = await handler.handle(
            DeductStockCommand(
                stock_item_id=item_id,
                tenant_id=tenant_id,
                quantity=schema.quantity,
                reason=schema.reason,
                reference_type=schema.reference_type,
                reference_id=schema.reference_id,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    await db.commit()
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.put(
    "/items/{item_id}/min-level",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Set minimum stock level",
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
    handler = SetMinStockLevelHandler(repo)
    item = await handler.handle(
        SetMinStockLevelCommand(
            stock_item_id=item_id,
            tenant_id=tenant_id,
            min_stock_level=schema.min_stock_level,
        )
    )
    await db.commit()
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.post(
    "/items/{item_id}/adjust",
    response_model=StockItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Adjust stock to an absolute quantity",
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
    movement_repo = SQLAlchemyStockMovementRepository(db)
    handler = AdjustStockHandler(item_repo, movement_repo)
    item = await handler.handle(
        AdjustStockCommand(
            stock_item_id=item_id,
            tenant_id=tenant_id,
            new_quantity=schema.new_quantity,
            reason=schema.reason,
        )
    )
    await db.commit()
    background_tasks.add_task(StockReadModelSync(mongo).sync, item)
    return _item_to_response(item)


@router.get(
    "/items/{item_id}/movements",
    response_model=list[StockMovementResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="Get movement history for a stock item",
)
async def get_stock_movements(
    item_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> list[StockMovementResponseSchema]:
    movement_repo = SQLAlchemyStockMovementRepository(db)
    movements = await movement_repo.find_by_stock_item(item_id, tenant_id)
    return [
        StockMovementResponseSchema(
            id=m.id,
            stock_item_id=m.stock_item_id,
            movement_type=m.movement_type.value,
            quantity_changed=m.quantity_changed,
            reason=m.reason,
            reference_type=m.reference_type,
            reference_id=m.reference_id,
            created_at=m.created_at.isoformat(),
        )
        for m in movements
    ]


# ─── Internal Helpers ─────────────────────────────────────────────────────────


def _item_to_response(item: object) -> StockItemResponseSchema:
    i: StockItem = item  # type: ignore[no-redef]
    return StockItemResponseSchema(
        id=i.id,
        name=i.name,
        category=i.category,
        current_quantity_amount=i.current_quantity.amount,
        current_quantity_unit=i.current_quantity.unit.value,
        min_stock_level=i.min_stock_level,
        is_active=i.is_active,
        is_low_stock=i.is_low_stock,
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
