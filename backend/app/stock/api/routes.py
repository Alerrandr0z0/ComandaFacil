from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.dependencies import CurrentTenantId, DbSession, MongoDB, require_permission
from app.menu.infrastructure.orm_models import MenuItemORM
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
from app.stock.domain.enums import TransactionType
from app.stock.domain.measured_quantity import MeasuredQuantity
from app.stock.domain.recipe import Recipe, RecipeIngredient
from app.stock.domain.stock_item import StockItem
from app.stock.infrastructure.mongo_read_repository import MongoStockReadRepository
from app.stock.infrastructure.orm_models import (
    RecipeIngredientORM,
    RecipeORM,
    StockItemORM,
    StockTransactionORM,
)
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyRecipeRepository,
    SQLAlchemyStockItemRepository,
)
from app.stock.infrastructure.stock_read_sync import StockReadModelSync

router = APIRouter(prefix="/stock", tags=["Stock"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────


class StockItemCreateSchema(BaseModel):
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
    reason: str = Field(default="", description="Justification / audit note for this adjustment")
    transaction_type: str = Field(
        default="ADJUSTMENT",
        description="Transaction type: ADJUSTMENT (inventory count), WASTE (loss/spoilage), PRODUCTION (manufactured)",
    )

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

    allowed_types = {"ADJUSTMENT", "WASTE", "PRODUCTION"}
    tx_type_str = schema.transaction_type.upper() if schema.transaction_type else "ADJUSTMENT"
    if tx_type_str not in allowed_types:
        raise HTTPException(
            status_code=422,
            detail=f"transaction_type inválido. Valores aceitos: {sorted(allowed_types)}",
        )

    await service.adjust(
        item_id,
        Decimal(str(schema.new_quantity)),
        tenant_id,
        reason=schema.reason,
        transaction_type=TransactionType(tx_type_str),
    )
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
    tenant_id: CurrentTenantId,
) -> list[StockMovementResponseSchema]:
    stmt = (
        select(StockTransactionORM)
        .join(StockItemORM, StockTransactionORM.stock_item_id == StockItemORM.id)
        .where(
            StockTransactionORM.stock_item_id == item_id,
            StockItemORM.tenant_id == tenant_id,
        )
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
            reason=t.reason,
            reference_type=None,
            reference_id=None,
            created_at=t.occurred_at.isoformat(),
        )
        for t in txs
    ]


# ─── Consumed-By Schema ────────────────────────────────────────────────────────


class ConsumedByItemSchema(BaseModel):
    menu_item_id: int
    menu_item_name: str
    quantity_value: float
    quantity_unit: str

    model_config = ConfigDict(frozen=True)


# ─── Recipe Schemas ────────────────────────────────────────────────────────────


class RecipeIngredientSchema(BaseModel):
    stock_item_id: int = Field(..., description="Stock item ID")
    quantity_value: float = Field(..., gt=0, description="Quantity needed")
    quantity_unit: str = Field(..., description="Measurement unit")

    model_config = ConfigDict(frozen=True)


class RecipeSaveSchema(BaseModel):
    ingredients: list[RecipeIngredientSchema] = Field(..., min_length=1)

    model_config = ConfigDict(frozen=True)


class RecipeResponseSchema(BaseModel):
    menu_item_id: int
    ingredients: list[RecipeIngredientSchema]

    model_config = ConfigDict(from_attributes=True, frozen=True)


class RecipeProduceResponseSchema(BaseModel):
    detail: str
    deducted_ingredients: list[dict[str, object]]

    model_config = ConfigDict(frozen=True)


# ─── Consumed-By Endpoint ─────────────────────────────────────────────────────


@router.get(
    "/items/{item_id}/consumed-by",
    response_model=list[ConsumedByItemSchema],
    status_code=status.HTTP_200_OK,
    summary="List menu items that consume this stock item",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def get_consumed_by(
    item_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> list[ConsumedByItemSchema]:
    """Returns all recipes (menu items) that use this stock item as an ingredient."""
    stmt = (
        select(
            RecipeORM.menu_item_id,
            MenuItemORM.name,
            RecipeIngredientORM.quantity_value,
            RecipeIngredientORM.quantity_unit,
        )
        .select_from(RecipeIngredientORM)
        .join(RecipeORM, RecipeIngredientORM.recipe_id == RecipeORM.id)
        .join(MenuItemORM, RecipeORM.menu_item_id == MenuItemORM.id)
        .where(
            RecipeIngredientORM.stock_item_id == item_id,
            RecipeORM.tenant_id == tenant_id,
            MenuItemORM.tenant_id == tenant_id,
        )
        .order_by(MenuItemORM.name)
    )
    res = await db.execute(stmt)
    rows = res.all()
    return [
        ConsumedByItemSchema(
            menu_item_id=row.menu_item_id,
            menu_item_name=row.name,
            quantity_value=float(row.quantity_value),
            quantity_unit=row.quantity_unit,
        )
        for row in rows
    ]


# ─── Recipe Endpoints ─────────────────────────────────────────────────────────


@router.get(
    "/recipes/{menu_item_id}",
    response_model=RecipeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get recipe for a menu item",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def get_recipe(
    menu_item_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> RecipeResponseSchema:
    item_repo = SQLAlchemyStockItemRepository(db)
    recipe_repo = SQLAlchemyRecipeRepository(db, item_repo)
    recipe = await recipe_repo.find_by_menu_item(menu_item_id, tenant_id)
    if not recipe:
        raise HTTPException(
            status_code=404,
            detail=f"Recipe para menu item '{menu_item_id}' não encontrada.",
        )
    return RecipeResponseSchema(
        menu_item_id=recipe.menu_item_id,
        ingredients=[
            RecipeIngredientSchema(
                stock_item_id=ing.stock_item.id,
                quantity_value=float(ing.quantity.value),
                quantity_unit=ing.quantity.unit,
            )
            for ing in recipe.get_ingredients()
        ],
    )


@router.put(
    "/recipes/{menu_item_id}",
    response_model=RecipeResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Save or update recipe for a menu item",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def save_recipe(
    menu_item_id: int,
    schema: RecipeSaveSchema,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> RecipeResponseSchema:
    item_repo = SQLAlchemyStockItemRepository(db)
    recipe_repo = SQLAlchemyRecipeRepository(db, item_repo)

    ingredients: list[RecipeIngredient] = []
    for ing in schema.ingredients:
        stock_item = await item_repo.find_by_id(ing.stock_item_id, tenant_id)
        if not stock_item:
            raise HTTPException(
                status_code=404,
                detail=f"Stock item '{ing.stock_item_id}' não encontrado.",
            )
        ingredients.append(
            RecipeIngredient(
                stock_item=stock_item,
                quantity=MeasuredQuantity(
                    value=Decimal(str(ing.quantity_value)), unit=ing.quantity_unit
                ),
            )
        )

    recipe = Recipe(
        id=0,
        menu_item_id=menu_item_id,
        tenant_id=tenant_id,
        ingredients=ingredients,
    )
    await recipe_repo.save(recipe)
    await db.commit()

    return RecipeResponseSchema(
        menu_item_id=recipe.menu_item_id,
        ingredients=[
            RecipeIngredientSchema(
                stock_item_id=ing.stock_item.id,
                quantity_value=float(ing.quantity.value),
                quantity_unit=ing.quantity.unit,
            )
            for ing in recipe.get_ingredients()
        ],
    )


@router.post(
    "/recipes/{menu_item_id}/produce",
    response_model=RecipeProduceResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Produce a menu item, deducting stock ingredients",
    dependencies=[Depends(require_permission("ADJUST_STOCK"))],
)
async def produce_recipe(
    menu_item_id: int,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
    quantity: int = Query(1, gt=0, description="Number of portions to produce"),
) -> RecipeProduceResponseSchema:
    item_repo = SQLAlchemyStockItemRepository(db)
    recipe_repo = SQLAlchemyRecipeRepository(db, item_repo)
    service = StockService(item_repo, recipe_repo)

    deducted: list[dict[str, object]] = []
    for _ in range(quantity):
        try:
            await service.deduct_by_recipe(menu_item_id, tenant_id)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e

    await db.commit()

    # Reload and sync all affected items
    recipe = await recipe_repo.find_by_menu_item(menu_item_id, tenant_id)
    if recipe:
        for ing in recipe.get_ingredients():
            item = await item_repo.find_by_id(ing.stock_item.id, tenant_id)
            if item:
                background_tasks.add_task(StockReadModelSync(mongo).sync, item)
                deducted.append(
                    {
                        "stock_item_id": ing.stock_item.id,
                        "name": ing.stock_item.name,
                        "quantity_deducted": float(ing.quantity.value),
                        "unit": ing.quantity.unit,
                    }
                )

    return RecipeProduceResponseSchema(
        detail=f"Produzido {quantity}x do item {menu_item_id} com dedução de estoque.",
        deducted_ingredients=deducted,
    )


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
