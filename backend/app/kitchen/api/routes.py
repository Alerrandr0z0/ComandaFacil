from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.dependencies import CurrentTenantId, DbSession, MongoDB, require_permission
from app.kitchen.application.commands import (
    CancelKitchenItemCommand,
    CancelKitchenItemHandler,
    MarkKitchenItemReadyCommand,
    MarkKitchenItemReadyHandler,
    PrepareKitchenItemCommand,
    PrepareKitchenItemHandler,
)
from app.kitchen.application.queries import (
    GetActiveKitchenItemsHandler,
    GetActiveKitchenItemsQuery,
)
from app.kitchen.infrastructure.kitchen_read_sync import KitchenReadModelSync
from app.kitchen.infrastructure.mongo_read_repository import MongoKitchenReadRepository
from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
from app.kitchen.infrastructure.websocket_manager import kds_ws_manager
from app.order.infrastructure.orm_models import OrderFormItemORM
from app.shared.database import get_mongo_db
from app.stock.application.commands import StockService
from app.stock.infrastructure.pg_repository import (
    SQLAlchemyRecipeRepository,
    SQLAlchemyStockItemRepository,
)

router = APIRouter(prefix="/kitchen", tags=["Kitchen"])


@router.patch("/items/{id}/prepare", dependencies=[Depends(require_permission("PREPARE_ITEM"))])
async def prepare_item(
    id: int,
    session: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the PREPARING state, scoped to tenant."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = PrepareKitchenItemHandler(repo)
    updated_item = await handler.handle(PrepareKitchenItemCommand(item_id=id, tenant_id=tenant_id))
    background_tasks.add_task(KitchenReadModelSync(mongo).sync, updated_item)
    return {"status": "success", "state": updated_item.state.name}


@router.patch("/items/{id}/ready", dependencies=[Depends(require_permission("PREPARE_ITEM"))])
async def mark_item_ready(
    id: int,
    session: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the READY state, scoped to tenant.
    Auto-deducts stock ingredients via recipe if one exists."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = MarkKitchenItemReadyHandler(repo)
    updated_item = await handler.handle(
        MarkKitchenItemReadyCommand(item_id=id, tenant_id=tenant_id)
    )

    # Auto-deduct stock via recipe
    try:
        stmt = select(OrderFormItemORM.menu_item_id).where(
            OrderFormItemORM.id == updated_item.correlation_id,
        )
        res = await session.execute(stmt)
        menu_item_id = res.scalar_one_or_none()
        if menu_item_id:
            item_repo = SQLAlchemyStockItemRepository(session)
            recipe_repo = SQLAlchemyRecipeRepository(session, item_repo)
            stock_service = StockService(item_repo, recipe_repo)
            await stock_service.deduct_by_recipe(menu_item_id, tenant_id)
            await session.commit()
    except Exception:
        pass  # Stock deduction is best-effort (e.g., no recipe or insufficient stock)

    background_tasks.add_task(KitchenReadModelSync(mongo).sync, updated_item)
    return {"status": "success", "state": updated_item.state.name}


@router.patch("/items/{id}/cancel", dependencies=[Depends(require_permission("PREPARE_ITEM"))])
async def cancel_item(
    id: int,
    session: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the CANCELLED state, scoped to tenant."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = CancelKitchenItemHandler(repo)
    updated_item = await handler.handle(CancelKitchenItemCommand(item_id=id, tenant_id=tenant_id))
    background_tasks.add_task(KitchenReadModelSync(mongo).sync, updated_item)
    return {"status": "success", "state": updated_item.state.name}


@router.get("/items", dependencies=[Depends(require_permission("PREPARE_ITEM"))])
async def get_active_items(
    station_type: str,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> list[dict[str, object]]:
    """Returns a list of all active (non-terminal) kitchen items for the specified station and tenant."""
    repo = MongoKitchenReadRepository(mongo)
    handler = GetActiveKitchenItemsHandler(repo)
    return await handler.handle(
        GetActiveKitchenItemsQuery(tenant_id=tenant_id, station_type=station_type)
    )


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    station_type: str,
    tenant_id: str,
) -> None:
    """Established a persistent WebSocket connection for real-time KDS updates.

    Segregated by tenant_id and filtered by the prep station_type.
    On connect, sends any existing READY items as ITEM_READY events
    so that recently-ready items appear as alerts on the orders page.
    """
    await kds_ws_manager.connect(websocket, tenant_id=tenant_id, station_type=station_type)

    # Send existing READY items to the newly connected client
    try:
        mongo_db = get_mongo_db()
        cursor = mongo_db["kitchen_read"].find(
            {
                "tenant_id": tenant_id,
                "station_type_cpy": station_type,
                "state": "READY",
            },
            {"_id": 0},
        )
        ready_items = await cursor.to_list(length=None)
        for item in ready_items:
            await websocket.send_json(
                {
                    "event": "ITEM_READY",
                    "item": {
                        "id": item["kitchen_item_id"],
                        "correlation_id": item.get("correlation_id"),
                        "name_cpy": item.get("name_cpy", ""),
                        "station_type_cpy": item.get("station_type_cpy", ""),
                        "state": "READY",
                    },
                }
            )
    except Exception:
        pass

    try:
        while True:
            # We keep the connection alive and listen for any incoming keepalive/pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        kds_ws_manager.disconnect(websocket, tenant_id=tenant_id, station_type=station_type)
    except Exception:
        kds_ws_manager.disconnect(websocket, tenant_id=tenant_id, station_type=station_type)
