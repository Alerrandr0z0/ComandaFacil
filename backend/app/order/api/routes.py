from __future__ import annotations

import contextlib
import datetime
import hashlib
import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select

from app.auth.infrastructure.orm_models import AuditLogORM
from app.dependencies import CurrentTenantId, DbSession, MongoDB, require_permission
from app.kitchen.domain.kitchen_item import KitchenOrderItem
from app.kitchen.infrastructure.kitchen_read_sync import KitchenReadModelSync
from app.kitchen.infrastructure.orm_models import KitchenOrderItemORM
from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
from app.kitchen.infrastructure.websocket_manager import kds_ws_manager
from app.menu.infrastructure.repositories import SQLAlchemyMenuItemRepository
from app.order.application.commands import (
    AddOrderItemCommand,
    AddOrderItemHandler,
    CancelOrderCommand,
    CancelOrderHandler,
    CreateOrderCommand,
    CreateOrderHandler,
    DeliverOrderCommand,
    DeliverOrderHandler,
    ProcessPaymentCommand,
    ProcessPaymentHandler,
    RequestPaymentCommand,
    RequestPaymentHandler,
)
from app.order.application.queries import (
    GetOrderHandler,
    GetOrderHistoryHandler,
    GetOrderHistoryQuery,
    GetOrderQuery,
)
from app.order.domain.fulfillment import Delivery, Table, Takeaway
from app.order.infrastructure.mongo_repository import OrderHistoryMongoRepository
from app.order.infrastructure.order_read_sync import OrderReadModelSync
from app.order.infrastructure.orm_models import OrderFormItemORM
from app.order.infrastructure.pg_repository import SQLAlchemyOrderRepository
from app.shared import database

if TYPE_CHECKING:
    from app.order.domain.order_form import OrderForm

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/order", tags=["Order"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────


class OrderCreateSchema(BaseModel):
    id: int | None = Field(
        default=None, description="Unique order identifier (auto-generated if omitted)"
    )
    display_code: str | None = Field(
        default=None,
        description="Manual code displayed on the order (e.g. MESA-004). Auto-generated if omitted.",
    )
    fulfillment_type: str = Field(
        ..., description="Type of fulfillment: TABLE, TAKEAWAY, or DELIVERY"
    )
    table_number: int | None = Field(default=None, description="Table number if TABLE")
    customer_name: str | None = Field(default=None, description="Customer name if TAKEAWAY")
    delivery_street: str | None = Field(default=None, description="Street name if DELIVERY")
    delivery_number: str | None = Field(
        default=None, description="House/Apartment number if DELIVERY"
    )
    delivery_neighborhood: str | None = Field(default=None, description="Neighborhood if DELIVERY")
    delivery_city: str | None = Field(default=None, description="City if DELIVERY")
    delivery_state: str | None = Field(default=None, description="State if DELIVERY")
    delivery_postal_code: str | None = Field(default=None, description="Postal code if DELIVERY")
    delivery_estimated_time: int = Field(
        default=40, description="Estimated delivery time in minutes"
    )
    delivery_tracking_code: int = Field(default=0, description="Delivery tracking code")

    model_config = ConfigDict(frozen=True)


class OrderItemAddSchema(BaseModel):
    id: int = Field(..., description="Unique item identifier")
    menu_item_id: int = Field(..., description="ID of the menuItem in the menu")
    name_cpy: str = Field(..., description="Snapshot name of the menuItem")
    price_cpy: Decimal = Field(..., description="Snapshot price of the menuItem")
    station_type_cpy: str = Field(..., description="Snapshot prep station type (e.g. Grill)")
    quantity: int = Field(..., gt=0, description="Quantity ordered")
    notes: str = Field(default="", description="Optional customization notes")

    model_config = ConfigDict(frozen=True)


class OrderItemResponseSchema(BaseModel):
    id: int
    menu_item_id: int
    name_cpy: str
    price_cpy: Decimal
    station_type_cpy: str
    quantity: int
    delivered_quantity: int = 0
    notes: str
    subtotal: Decimal
    status: str
    kitchen_states: list[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True, frozen=True)


class FulfillmentResponseSchema(BaseModel):
    type: str | None
    fee: Decimal
    table_number: int | None = None
    customer_name: str | None = None
    delivery_street: str | None = None
    delivery_number: str | None = None
    delivery_neighborhood: str | None = None
    delivery_city: str | None = None
    delivery_state: str | None = None
    delivery_postal_code: str | None = None
    delivery_estimated_time: int | None = None
    delivery_tracking_code: int | None = None
    delivery_state_name: str | None = None

    model_config = ConfigDict(from_attributes=True, frozen=True)


class OrderResponseSchema(BaseModel):
    id: int
    tenant_id: str
    display_code: str
    state: str
    payment_requested: bool
    total: Decimal
    fulfillment: FulfillmentResponseSchema
    items: list[OrderItemResponseSchema] = []
    created_at: datetime.datetime

    model_config = ConfigDict(from_attributes=True, frozen=True)


# ─── REST Endpoints ───────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Order Form",
    dependencies=[Depends(require_permission("CREATE_ORDER"))],
)
async def create_order(
    schema: OrderCreateSchema,
    tenant_id: CurrentTenantId,
    db: DbSession,
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = CreateOrderHandler(repo)
    command = CreateOrderCommand(
        id=schema.id,
        tenant_id=tenant_id,
        display_code=schema.display_code,
        fulfillment_type=schema.fulfillment_type,
        table_number=schema.table_number,
        customer_name=schema.customer_name,
        delivery_street=schema.delivery_street,
        delivery_number=schema.delivery_number,
        delivery_neighborhood=schema.delivery_neighborhood,
        delivery_city=schema.delivery_city,
        delivery_state=schema.delivery_state,
        delivery_postal_code=schema.delivery_postal_code,
        delivery_estimated_time=schema.delivery_estimated_time,
        delivery_tracking_code=schema.delivery_tracking_code,
    )
    try:
        order = await handler.handle(command)
        await db.commit()
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "",
    response_model=list[OrderResponseSchema],
    status_code=status.HTTP_200_OK,
    summary="List all active Order Forms",
    dependencies=[Depends(require_permission("CREATE_ORDER"))],
)
async def list_active_orders(
    db: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> list[OrderResponseSchema]:
    repo = SQLAlchemyOrderRepository(db)
    orders = await repo.find_all_active_by_tenant(tenant_id)
    return [await _enrich_order(_order_to_response(o), mongo) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get active Order Form by ID",
    dependencies=[Depends(require_permission("CREATE_ORDER"))],
)
async def get_order(
    order_id: int,
    db: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = GetOrderHandler(repo)
    order = await handler.handle(GetOrderQuery(order_id=order_id, tenant_id=tenant_id))
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comanda '{order_id}' não encontrada.",
        )
    return await _enrich_order(_order_to_response(order), mongo)


def _get_notes_condition(notes: str) -> Any:
    """Helper to build notes matching condition, handling None vs empty string."""
    if not notes or notes.strip() == "":
        return or_(
            KitchenOrderItemORM.notes.is_(None),
            KitchenOrderItemORM.notes == "",
        )
    return KitchenOrderItemORM.notes == notes


async def _notify_kitchen(
    correlation_id: int,
    menu_item_id: int,
    notes: str,
    tenant_id: str,
    quantity: int = 1,
    mongo: MongoDB | None = None,
) -> None:
    """Helper to synchronously send new order items to the kitchen (called from endpoint).
    When quantity > 1, creates one KitchenOrderItem per unit so each can be tracked individually."""
    sf = database.session_factory
    if sf is None:
        logger.warning("session_factory is None, skipping kitchen notification")
        return

    async for session in database.get_async_session():
        item_repo = SQLAlchemyMenuItemRepository(session)
        menu_item = await item_repo.find_by_id(menu_item_id, tenant_id)
        if not menu_item:
            logger.warning("Menu item %s not found for tenant %s", menu_item_id, tenant_id)
            return

        kitchen_repo = SQLAlchemyKitchenOrderItemRepository(session)
        try:
            notes_cond = _get_notes_condition(notes)

            # Query for surplus items of the same dish and tenant in FIFO order (by id asc)
            stmt = (
                select(KitchenOrderItemORM)
                .where(
                    KitchenOrderItemORM.state == "SURPLUS",
                    KitchenOrderItemORM.name_cpy == menu_item.name,
                    KitchenOrderItemORM.tenant_id == tenant_id,
                    notes_cond,
                )
                .order_by(KitchenOrderItemORM.id.asc())
            )
            result = await session.execute(stmt)
            surplus_orms = list(result.scalars().all())

            items_created: list[KitchenOrderItem] = []
            for seq in range(quantity):
                unique_id = correlation_id * 1000 + seq
                existing = await kitchen_repo.find_by_id(unique_id, tenant_id)
                if existing:
                    items_created.append(existing)
                    continue

                if surplus_orms:
                    surplus_orm = surplus_orms.pop(0)
                    item = kitchen_repo.map_to_domain(surplus_orm)
                    item.reclaim(correlation_id)
                    item.notes = notes
                    await kitchen_repo.save(item)
                    items_created.append(item)

                    # Notify KDS clients of reclaimed ready item
                    await kds_ws_manager.broadcast_to_station(
                        tenant_id=tenant_id,
                        station_type=menu_item.station_type,
                        event_data={
                            "event": "ITEM_READY",
                            "item": {
                                "id": item.id,
                                "correlation_id": item.correlation_id,
                                "name_cpy": item.name_cpy,
                                "station_type_cpy": item.station_type_cpy,
                                "state": item.state.name,
                                "notes": item.notes,
                            },
                        },
                    )
                else:
                    item = KitchenOrderItem(
                        id=unique_id,
                        correlation_id=correlation_id,
                        name_cpy=menu_item.name,
                        station_type_cpy=menu_item.station_type,
                        tenant_id=tenant_id,
                        preparation_profile=menu_item.preparation_profile.value,
                        notes=notes,
                    )
                    await kitchen_repo.save(item)
                    items_created.append(item)

                    # Notify KDS clients connected to this station
                    await kds_ws_manager.broadcast_to_station(
                        tenant_id=tenant_id,
                        station_type=menu_item.station_type,
                        event_data={
                            "event": "ITEM_RECEIVED",
                            "item": {
                                "id": item.id,
                                "correlation_id": item.correlation_id,
                                "name_cpy": item.name_cpy,
                                "station_type_cpy": item.station_type_cpy,
                                "state": item.state.name,
                                "notes": item.notes,
                                "menu_item_id": menu_item_id,
                            },
                        },
                    )

            await session.commit()
            logger.info(
                "Kitchen items created/reclaimed for correlation_id=%s qty=%s",
                correlation_id,
                quantity,
            )

            if mongo is not None:
                sync = KitchenReadModelSync(mongo)
                for kitem in items_created:
                    await sync.sync(kitem, menu_item_id=menu_item_id)
                logger.info("Kitchen items synced to MongoDB for correlation_id=%s", correlation_id)
        except Exception:
            logger.exception(
                "Failed to notify kitchen for correlation_id=%s menu_item_id=%s",
                correlation_id,
                menu_item_id,
            )


@router.post(
    "/{order_id}/items",
    response_model=OrderItemResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add an item to an active Order Form",
    dependencies=[Depends(require_permission("CREATE_ORDER"))],
)
async def add_order_item(
    order_id: int,
    schema: OrderItemAddSchema,
    db: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> OrderItemResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = AddOrderItemHandler(repo)
    command = AddOrderItemCommand(
        order_id=order_id,
        tenant_id=tenant_id,
        item_id=schema.id,
        menu_item_id=schema.menu_item_id,
        name_cpy=schema.name_cpy,
        price_cpy=schema.price_cpy,
        station_type_cpy=schema.station_type_cpy,
        quantity=schema.quantity,
        notes=schema.notes,
    )
    try:
        item = await handler.handle(command)
        await db.commit()

        # Notify the KDS context synchronously
        await _notify_kitchen(
            correlation_id=item.id,
            menu_item_id=item.menu_item_id,
            notes=item.notes,
            tenant_id=tenant_id,
            quantity=item.quantity,
            mongo=mongo,
        )

        res_schema = OrderItemResponseSchema(
            id=item.id,
            menu_item_id=item.menu_item_id,
            name_cpy=item.name_cpy,
            price_cpy=item.price_cpy.amount,
            station_type_cpy=item.station_type_cpy,
            quantity=item.quantity,
            delivered_quantity=item.delivered_quantity,
            notes=item.notes,
            subtotal=item.calculate_subtotal().amount,
            status=item.status.value,
        )
        return await _enrich_order_item(res_schema, tenant_id, mongo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/{order_id}/request-payment",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Request payment (lock) for an active Order Form",
    dependencies=[Depends(require_permission("CREATE_ORDER"))],
)
async def request_payment(
    order_id: int,
    db: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = RequestPaymentHandler(repo)
    try:
        order = await handler.handle(RequestPaymentCommand(order_id=order_id, tenant_id=tenant_id))
        await db.commit()
        return await _enrich_order(_order_to_response(order), mongo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/{order_id}/process-payment",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Process payment for an active Order Form",
    dependencies=[Depends(require_permission("CLOSE_ORDER"))],
)
async def process_payment(
    order_id: int,
    db: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = ProcessPaymentHandler(repo)
    try:
        order = await handler.handle(ProcessPaymentCommand(order_id=order_id, tenant_id=tenant_id))
        await db.commit()
        return await _enrich_order(_order_to_response(order), mongo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


async def _delete_kitchen_read_models(
    order: OrderForm, tenant_id: str, mongo: MongoDB | None
) -> None:
    if mongo is None:
        return
    try:
        order_item_ids = [item.id for item in order.items]
        await mongo["kitchen_read"].delete_many(
            {"correlation_id": {"$in": order_item_ids}, "tenant_id": tenant_id}
        )
    except Exception:
        logger.exception("Failed to delete kitchen read models on order cancellation")


async def _broadcast_kitchen_cancellations(order: OrderForm, tenant_id: str) -> None:
    async for session in database.get_async_session():
        for order_item in order.items:
            stmt = select(KitchenOrderItemORM).where(
                KitchenOrderItemORM.correlation_id == order_item.id,
                KitchenOrderItemORM.tenant_id == tenant_id,
            )
            result = await session.execute(stmt)
            orms = result.scalars().all()
            for orm in orms:
                with contextlib.suppress(Exception):
                    await kds_ws_manager.broadcast_to_station(
                        tenant_id=tenant_id,
                        station_type=order_item.station_type_cpy,
                        event_data={
                            "event": "ITEM_CANCELLED",
                            "item": {
                                "id": orm.id,
                                "correlation_id": order_item.id,
                                "state": "CANCELLED",
                            },
                        },
                    )


async def _cancel_pg_kitchen_items(
    order: OrderForm,
    tenant_id: str,
    mongo: MongoDB | None = None,
) -> None:
    async for session in database.get_async_session():
        kitchen_repo = SQLAlchemyKitchenOrderItemRepository(session)
        items_to_sync: list[KitchenOrderItem] = []
        updated_any = False
        for order_item in order.items:
            # Only ready items that are NOT yet delivered can go to surplus
            undelivered_qty = max(0, order_item.quantity - order_item.delivered_quantity)
            surplus_count = 0

            stmt = select(KitchenOrderItemORM).where(
                KitchenOrderItemORM.correlation_id == order_item.id,
                KitchenOrderItemORM.tenant_id == tenant_id,
            )
            result = await session.execute(stmt)
            orms = result.scalars().all()
            for orm in orms:
                kitchen_item = kitchen_repo.map_to_domain(orm)
                if kitchen_item.state.name == "READY":
                    if surplus_count < undelivered_qty:
                        kitchen_item.cancel()  # Transitions to Surplus
                        kitchen_item.correlation_id = 0
                        await kitchen_repo.save(kitchen_item)
                        items_to_sync.append(kitchen_item)
                        surplus_count += 1
                        updated_any = True
                    # If already delivered, it stays in READY state (already consumed on table)
                elif kitchen_item.state.name not in ("CANCELLED", "SURPLUS"):
                    kitchen_item.cancel()  # Transitions to Cancelled
                    await kitchen_repo.save(kitchen_item)
                    updated_any = True

        if updated_any:
            await session.commit()
            logger.info("Updated kitchen items in PG for order cancellation")
            if mongo is not None and items_to_sync:
                sync = KitchenReadModelSync(mongo)
                for kitem in items_to_sync:
                    await sync.sync(kitem)
                logger.info("Synced updated SURPLUS kitchen items to MongoDB")


async def _cancel_kitchen_items(
    order: OrderForm,
    tenant_id: str,
    mongo: MongoDB | None = None,
) -> None:
    """Cancel associated kitchen items for all order items when an order is cancelled.
    Iterates over all items (one per quantity unit) matching each correlation_id."""
    sf = database.session_factory
    if sf is None:
        return

    # 1. Delete all kitchen read models for this order immediately from MongoDB
    await _delete_kitchen_read_models(order, tenant_id, mongo)

    # 2. Broadcast ITEM_CANCELLED event to all KDS clients for each unit
    await _broadcast_kitchen_cancellations(order, tenant_id)

    # 3. Transition states in PostgreSQL and sync surplus items to MongoDB
    await _cancel_pg_kitchen_items(order, tenant_id, mongo)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Cancel an active Order Form",
    dependencies=[Depends(require_permission("CLOSE_ORDER"))],
)
async def cancel_order(
    order_id: int,
    db: DbSession,
    background_tasks: BackgroundTasks,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = CancelOrderHandler(repo)
    try:
        order = await handler.handle(CancelOrderCommand(order_id=order_id, tenant_id=tenant_id))
        # Cascade cancellation to order items and associated kitchen items
        for item in order.items:
            item.mark_canceled()
        await repo.save(order)
        await db.commit()
        # Sync to history read model (MongoDB)
        mongo_repo = OrderHistoryMongoRepository(mongo)
        await mongo_repo.save(order)
        background_tasks.add_task(_cancel_kitchen_items, order, tenant_id, mongo)
        return await _enrich_order(_order_to_response(order), mongo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.patch(
    "/items/{item_id}/deliver",
    response_model=OrderItemResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Deliver order item units. Remaining quantity when omitted.",
    dependencies=[Depends(require_permission("CREATE_ORDER"))],
)
async def deliver_order_item(
    item_id: int,
    db: DbSession,
    mongo: MongoDB,
    tenant_id: CurrentTenantId,
    qty: int = Query(default=0, description="Quantity to deliver (0 = all remaining)"),
) -> OrderItemResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    order = await repo.find_by_item_id(item_id, tenant_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Item '{item_id}' não encontrado.",
        )
    item = next((i for i in order.items if i.id == item_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado na comanda.")
    item.mark_delivered(qty=qty)
    await repo.save(order)

    # Remove delivered kitchen items from MongoDB — if partial, remove only one
    try:
        if item.delivered_quantity >= item.quantity or qty == 0:
            await mongo["kitchen_read"].delete_many(
                {"correlation_id": item_id, "tenant_id": tenant_id}
            )
        else:
            # Remove one READY kitchen item at a time
            ready_item = await mongo["kitchen_read"].find_one_and_delete(
                {
                    "correlation_id": item_id,
                    "tenant_id": tenant_id,
                    "state": "READY",
                },
            )
            if ready_item is None:
                # Fallback: delete any item for this correlation
                await mongo["kitchen_read"].delete_one(
                    {"correlation_id": item_id, "tenant_id": tenant_id}
                )
    except Exception:
        pass

    await db.commit()
    res_schema = OrderItemResponseSchema(
        id=item.id,
        menu_item_id=item.menu_item_id,
        name_cpy=item.name_cpy,
        price_cpy=item.price_cpy.amount,
        station_type_cpy=item.station_type_cpy,
        quantity=item.quantity,
        delivered_quantity=item.delivered_quantity,
        notes=item.notes,
        subtotal=item.calculate_subtotal().amount,
        status=item.status.value,
    )
    return await _enrich_order_item(res_schema, tenant_id, mongo)


@router.post(
    "/{order_id}/deliver",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Deliver/complete an active Order Form, close it, and sync to MongoDB",
    dependencies=[Depends(require_permission("CLOSE_ORDER"))],
)
async def deliver_order(
    order_id: int,
    db: DbSession,
    mongo: MongoDB,
    background_tasks: BackgroundTasks,
    tenant_id: CurrentTenantId,
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    mongo_repo = OrderHistoryMongoRepository(mongo)
    handler = DeliverOrderHandler(repo, mongo_repo)
    try:
        order = await handler.handle(DeliverOrderCommand(order_id=order_id, tenant_id=tenant_id))
        await db.commit()
        background_tasks.add_task(OrderReadModelSync(mongo).sync, order)
        return await _enrich_order(_order_to_response(order), mongo)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get(
    "/history/all",
    response_model=list[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get completed Order History read models from MongoDB",
    dependencies=[Depends(require_permission("CLOSE_ORDER"))],
)
async def get_order_history(
    tenant_id: CurrentTenantId,
    mongo: MongoDB,
) -> list[dict[str, Any]]:
    mongo_repo = OrderHistoryMongoRepository(mongo)
    handler = GetOrderHistoryHandler(mongo_repo)
    return await handler.handle(GetOrderHistoryQuery(tenant_id=tenant_id))


@router.get(
    "/{order_id}/timeline",
    response_model=list[dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get timeline/audit trail for a specific order",
    dependencies=[Depends(require_permission("CREATE_ORDER"))],
)
async def get_order_timeline(
    order_id: int,
    db: DbSession,
    tenant_id: CurrentTenantId,
) -> list[dict[str, Any]]:
    try:
        t_id = int(tenant_id)
    except ValueError:
        t_id = int(hashlib.sha256(str(tenant_id).encode("utf-8")).hexdigest(), 16) % 1000000

    # 1. Fetch order logs
    stmt_order = select(AuditLogORM).where(
        AuditLogORM.tenant_id == t_id,
        AuditLogORM.entity_type == "order",
        AuditLogORM.entity_id == str(order_id),
    )
    result_order = await db.execute(stmt_order)
    logs = list(result_order.scalars().all())

    # 2. Get kitchen item IDs associated with this order
    stmt_items = select(OrderFormItemORM.id).where(OrderFormItemORM.order_id == order_id)
    result_items = await db.execute(stmt_items)
    item_ids = list(result_items.scalars().all())

    if item_ids:
        stmt_kitchen = select(KitchenOrderItemORM.id).where(
            KitchenOrderItemORM.correlation_id.in_(item_ids),
            KitchenOrderItemORM.tenant_id == tenant_id,
        )
        result_kitchen = await db.execute(stmt_kitchen)
        k_ids = [str(kid) for kid in result_kitchen.scalars().all()]

        if k_ids:
            stmt_kitchen_logs = select(AuditLogORM).where(
                AuditLogORM.tenant_id == t_id,
                AuditLogORM.entity_type == "kitchen_item",
                AuditLogORM.entity_id.in_(k_ids),
            )
            result_klogs = await db.execute(stmt_kitchen_logs)
            logs.extend(result_klogs.scalars().all())

    # Sort by created_at ascending
    logs.sort(key=lambda o: o.created_at or datetime.datetime.min.replace(tzinfo=datetime.UTC))

    return [
        {
            "id": o.id,
            "actor_name": o.actor_name,
            "action": o.action,
            "entity_type": o.entity_type,
            "entity_id": o.entity_id,
            "details": o.details,
            "created_at": o.created_at.isoformat() if o.created_at else None,
        }
        for o in logs
    ]


# ─── Internal Helpers ─────────────────────────────────────────────────────────


def _order_to_response(order: OrderForm) -> OrderResponseSchema:
    """Transforms a domain OrderForm aggregate into a Pydantic response schema."""
    strat = order.fulfillment_strategy
    fee_val = Decimal("0.00")
    fulfillment_response: dict[str, Any] = {
        "type": None,
        "fee": fee_val,
    }

    if strat is not None:
        fee_val = strat.calculate_fee().amount
        fulfillment_response["type"] = strat.name
        fulfillment_response["fee"] = fee_val

        if isinstance(strat, Table):
            fulfillment_response["table_number"] = strat.table_num
        elif isinstance(strat, Takeaway):
            fulfillment_response["customer_name"] = strat.customer_name
        elif isinstance(strat, Delivery):
            fulfillment_response["delivery_street"] = strat.address.street
            fulfillment_response["delivery_number"] = strat.address.number
            fulfillment_response["delivery_neighborhood"] = strat.address.neighborhood
            fulfillment_response["delivery_city"] = strat.address.city
            fulfillment_response["delivery_state"] = strat.address.state
            fulfillment_response["delivery_postal_code"] = strat.address.postal_code
            fulfillment_response["delivery_estimated_time"] = strat.estimated_time
            fulfillment_response["delivery_tracking_code"] = strat.tracking_code
            fulfillment_response["delivery_state_name"] = strat.state.name

    return OrderResponseSchema(
        id=order.id,
        tenant_id=order.tenant_id,
        display_code=order.display_code,
        state=order.state.name,
        payment_requested=order._payment_requested,  # type: ignore[reportPrivateUsage]
        total=order.total().amount,
        fulfillment=FulfillmentResponseSchema(**fulfillment_response),
        created_at=order.created_at,
        items=[
            OrderItemResponseSchema(
                id=item.id,
                menu_item_id=item.menu_item_id,
                name_cpy=item.name_cpy,
                price_cpy=item.price_cpy.amount,
                station_type_cpy=item.station_type_cpy,
                quantity=item.quantity,
                delivered_quantity=item.delivered_quantity,
                notes=item.notes,
                subtotal=item.calculate_subtotal().amount,
                status=item.status.value,
            )
            for item in order.items
        ],
    )


async def _enrich_order(
    order_res: OrderResponseSchema,
    mongo: MongoDB,
) -> OrderResponseSchema:
    item_ids = [item.id for item in order_res.items]
    if not item_ids:
        return order_res

    cursor = mongo["kitchen_read"].find(
        {"correlation_id": {"$in": item_ids}, "tenant_id": order_res.tenant_id}
    )
    docs = await cursor.to_list(length=None)

    states_by_item: dict[int, list[str]] = {}
    for doc in docs:
        corr_id = doc.get("correlation_id")
        state = doc.get("state")
        if corr_id is not None and state is not None:
            states_by_item.setdefault(corr_id, []).append(state)

    enriched_items = []
    order_map = {"WAITING": 0, "PREPARING": 1, "READY": 2, "CANCELLED": 3}

    def _sort_key(s: str) -> int:
        return order_map.get(s, 99)

    for item in order_res.items:
        k_states = states_by_item.get(item.id, [])
        k_states.sort(key=_sort_key)

        missing_count = max(0, item.quantity - len(k_states))
        k_states.extend(["DELIVERED"] * missing_count)
        k_states = k_states[: item.quantity]

        enriched_items.append(
            OrderItemResponseSchema(
                id=item.id,
                menu_item_id=item.menu_item_id,
                name_cpy=item.name_cpy,
                price_cpy=item.price_cpy,
                station_type_cpy=item.station_type_cpy,
                quantity=item.quantity,
                delivered_quantity=item.delivered_quantity,
                notes=item.notes,
                subtotal=item.subtotal,
                status=item.status,
                kitchen_states=k_states,
            )
        )

    return OrderResponseSchema(
        id=order_res.id,
        tenant_id=order_res.tenant_id,
        display_code=order_res.display_code,
        state=order_res.state,
        payment_requested=order_res.payment_requested,
        total=order_res.total,
        fulfillment=order_res.fulfillment,
        items=enriched_items,
        created_at=order_res.created_at,
    )


async def _enrich_order_item(
    item: OrderItemResponseSchema,
    tenant_id: str,
    mongo: MongoDB,
) -> OrderItemResponseSchema:
    cursor = mongo["kitchen_read"].find({"correlation_id": item.id, "tenant_id": tenant_id})
    docs = await cursor.to_list(length=None)
    k_states = [doc.get("state") for doc in docs if doc.get("state")]

    order_map = {"WAITING": 0, "PREPARING": 1, "READY": 2, "CANCELLED": 3}

    def _sort_key_item(s: str) -> int:
        return order_map.get(s, 99)

    k_states.sort(key=_sort_key_item)

    missing_count = max(0, item.quantity - len(k_states))
    k_states.extend(["DELIVERED"] * missing_count)
    k_states = k_states[: item.quantity]

    return OrderItemResponseSchema(
        id=item.id,
        menu_item_id=item.menu_item_id,
        name_cpy=item.name_cpy,
        price_cpy=item.price_cpy,
        station_type_cpy=item.station_type_cpy,
        quantity=item.quantity,
        delivered_quantity=item.delivered_quantity,
        notes=item.notes,
        subtotal=item.subtotal,
        status=item.status,
        kitchen_states=k_states,
    )
