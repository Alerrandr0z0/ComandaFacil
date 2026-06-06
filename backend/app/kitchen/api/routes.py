from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect

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
    """Transitions a kitchen order item to the READY state, scoped to tenant."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = MarkKitchenItemReadyHandler(repo)
    updated_item = await handler.handle(
        MarkKitchenItemReadyCommand(item_id=id, tenant_id=tenant_id)
    )
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
    """
    await kds_ws_manager.connect(websocket, tenant_id=tenant_id, station_type=station_type)
    try:
        while True:
            # We keep the connection alive and listen for any incoming keepalive/pings
            await websocket.receive_text()
    except WebSocketDisconnect:
        kds_ws_manager.disconnect(websocket, tenant_id=tenant_id, station_type=station_type)
    except Exception:
        kds_ws_manager.disconnect(websocket, tenant_id=tenant_id, station_type=station_type)
