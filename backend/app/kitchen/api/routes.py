from __future__ import annotations

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.dependencies import CurrentTenantId, DbSession
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
from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
from app.kitchen.infrastructure.websocket_manager import kds_ws_manager

router = APIRouter(prefix="/kitchen", tags=["Kitchen"])


@router.patch("/items/{id}/prepare")
async def prepare_item(
    id: int,
    session: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the PREPARING state."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    item = await repo.find_by_id(id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=f"Kitchen item {id} not found.")

    handler = PrepareKitchenItemHandler(repo)
    updated_item = await handler.handle(PrepareKitchenItemCommand(item_id=id))
    return {"status": "success", "state": updated_item.state.name}


@router.patch("/items/{id}/ready")
async def mark_item_ready(
    id: int,
    session: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the READY state."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    item = await repo.find_by_id(id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=f"Kitchen item {id} not found.")

    handler = MarkKitchenItemReadyHandler(repo)
    updated_item = await handler.handle(MarkKitchenItemReadyCommand(item_id=id))
    return {"status": "success", "state": updated_item.state.name}


@router.patch("/items/{id}/cancel")
async def cancel_item(
    id: int,
    session: DbSession,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the CANCELLED state."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    item = await repo.find_by_id(id)
    if not item or item.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail=f"Kitchen item {id} not found.")

    handler = CancelKitchenItemHandler(repo)
    updated_item = await handler.handle(CancelKitchenItemCommand(item_id=id))
    return {"status": "success", "state": updated_item.state.name}


@router.get("/items")
async def get_active_items(
    station_type: str,
    session: DbSession,
    tenant_id: CurrentTenantId,
) -> list[dict[str, str | int]]:
    """Returns a list of all active (non-terminal) kitchen items for the specified station and tenant."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = GetActiveKitchenItemsHandler(repo)
    items = await handler.handle(
        GetActiveKitchenItemsQuery(tenant_id=tenant_id, station_type=station_type)
    )
    return [
        {
            "id": item.id,
            "correlation_id": item.correlation_id,
            "name_cpy": item.name_cpy,
            "station_type_cpy": item.station_type_cpy,
            "state": item.state.name,
        }
        for item in items
    ]


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
