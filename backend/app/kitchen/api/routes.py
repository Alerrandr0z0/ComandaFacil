from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field

from app.dependencies import CurrentTenantId, DbSession, MongoDB, require_permission
from app.kitchen.application.commands import (
    ApproveKitchenCancelCommand,
    ApproveKitchenCancelHandler,
    CancelKitchenItemCommand,
    CancelKitchenItemHandler,
    MarkKitchenItemReadyCommand,
    MarkKitchenItemReadyHandler,
    PrepareKitchenItemCommand,
    PrepareKitchenItemHandler,
    RejectKitchenCancelCommand,
    RejectKitchenCancelHandler,
)
from app.kitchen.application.queries import (
    GetActiveKitchenItemsHandler,
    GetActiveKitchenItemsQuery,
)
from app.kitchen.infrastructure.kitchen_read_sync import KitchenReadModelSync
from app.kitchen.infrastructure.mongo_read_repository import MongoKitchenReadRepository
from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
from app.kitchen.infrastructure.websocket_manager import kds_ws_manager
from app.shared.database import get_mongo_db

router = APIRouter(prefix="/kitchen", tags=["Kitchen"])


@router.patch("/items/{id}/prepare", dependencies=[Depends(require_permission("PREPARE_ITEM"))])
async def prepare_item(
    id: int,
    session: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the PREPARING state, scoped to tenant."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = PrepareKitchenItemHandler(repo)
    updated_item = await handler.handle(PrepareKitchenItemCommand(item_id=id, tenant_id=tenant_id))
    await session.commit()
    sync = KitchenReadModelSync(mongo)
    await sync.sync(updated_item)
    return {"status": "success", "state": updated_item.state.name}


@router.patch("/items/{id}/ready", dependencies=[Depends(require_permission("PREPARE_ITEM"))])
async def mark_item_ready(
    id: int,
    session: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the READY state, scoped to tenant."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = MarkKitchenItemReadyHandler(repo)
    try:
        updated_item = await handler.handle(
            MarkKitchenItemReadyCommand(item_id=id, tenant_id=tenant_id)
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    await session.commit()
    sync = KitchenReadModelSync(mongo)
    await sync.sync(updated_item)
    return {"status": "success", "state": updated_item.state.name}


@router.patch("/items/{id}/cancel", dependencies=[Depends(require_permission("PREPARE_ITEM"))])
async def cancel_item(
    id: int,
    session: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Transitions a kitchen order item to the CANCELLED state, scoped to tenant."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = CancelKitchenItemHandler(repo)
    updated_item = await handler.handle(CancelKitchenItemCommand(item_id=id, tenant_id=tenant_id))
    await session.commit()
    sync = KitchenReadModelSync(mongo)
    await sync.sync(updated_item)
    return {"status": "success", "state": updated_item.state.name}


class ApproveCancelSchema(BaseModel):
    mode: str = Field(..., description="Approval mode: 'WASTE' or 'SURPLUS'")


@router.post(
    "/items/{id}/cancel/approve", dependencies=[Depends(require_permission("PREPARE_ITEM"))]
)
async def approve_cancel_item(
    id: int,
    body: ApproveCancelSchema,
    session: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Approves a cancel request, transitioning the item to CANCELLED or SURPLUS."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = ApproveKitchenCancelHandler(repo)
    updated_item = await handler.handle(
        ApproveKitchenCancelCommand(item_id=id, tenant_id=tenant_id, mode=body.mode)
    )
    await session.commit()
    sync = KitchenReadModelSync(mongo)
    await sync.sync(updated_item)
    return {"status": "success", "state": updated_item.state.name}


@router.post(
    "/items/{id}/cancel/reject", dependencies=[Depends(require_permission("PREPARE_ITEM"))]
)
async def reject_cancel_item(
    id: int,
    session: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> dict[str, str]:
    """Rejects a cancel request, reverting the item to its previous state."""
    repo = SQLAlchemyKitchenOrderItemRepository(session)
    handler = RejectKitchenCancelHandler(repo)
    updated_item = await handler.handle(RejectKitchenCancelCommand(item_id=id, tenant_id=tenant_id))
    await session.commit()
    sync = KitchenReadModelSync(mongo)
    await sync.sync(updated_item)
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

    # Send existing READY items (completed within the last 15 minutes) to the newly connected client
    try:
        mongo_db = get_mongo_db()
        fifteen_minutes_ago = datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=15)
        cursor = mongo_db["kitchen_read"].find(
            {
                "tenant_id": tenant_id,
                "station_type_cpy": station_type,
                "state": "READY",
                "completed_at": {"$gte": fifteen_minutes_ago},
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
                        "menu_item_id": item.get("menu_item_id"),
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
