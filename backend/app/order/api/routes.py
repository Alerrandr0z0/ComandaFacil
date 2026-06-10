from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.dependencies import CurrentTenantId, DbSession, MongoDB, require_permission
from app.kitchen.application.commands import KitchenService
from app.kitchen.infrastructure.kitchen_read_sync import KitchenReadModelSync
from app.kitchen.infrastructure.pg_repository import SQLAlchemyKitchenOrderItemRepository
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
    notes: str
    subtotal: Decimal
    status: str

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
    db: DbSession, tenant_id: CurrentTenantId
) -> list[OrderResponseSchema]:
    repo = SQLAlchemyOrderRepository(db)
    orders = await repo.find_all_active_by_tenant(tenant_id)
    return [_order_to_response(o) for o in orders]


@router.get(
    "/{order_id}",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get active Order Form by ID",
    dependencies=[Depends(require_permission("CREATE_ORDER"))],
)
async def get_order(
    order_id: int, db: DbSession, tenant_id: CurrentTenantId
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = GetOrderHandler(repo)
    order = await handler.handle(GetOrderQuery(order_id=order_id, tenant_id=tenant_id))
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comanda '{order_id}' não encontrada.",
        )
    return _order_to_response(order)


async def _notify_kitchen(
    correlation_id: int,
    menu_item_id: int,
    notes: str,
    tenant_id: str,
    mongo: MongoDB | None = None,
) -> None:
    """Helper to synchronously send new order items to the kitchen (called from endpoint)."""
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
        service = KitchenService(kitchen_repo)
        try:
            item = await service.receive_item(
                correlation_id=correlation_id,
                name_cpy=menu_item.name,
                station_type_cpy=menu_item.station_type,
                tenant_id=tenant_id,
                preparation_profile=menu_item.preparation_profile.value,
                notes=notes,
            )
            await session.commit()
            logger.info("Kitchen item created for correlation_id=%s", correlation_id)
            if mongo is not None:
                await KitchenReadModelSync(mongo).sync(item)
                logger.info("Kitchen item synced to MongoDB for correlation_id=%s", correlation_id)
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
            mongo=mongo,
        )

        return OrderItemResponseSchema(
            id=item.id,
            menu_item_id=item.menu_item_id,
            name_cpy=item.name_cpy,
            price_cpy=item.price_cpy.amount,
            station_type_cpy=item.station_type_cpy,
            quantity=item.quantity,
            notes=item.notes,
            subtotal=item.calculate_subtotal().amount,
            status=item.status.value,
        )
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
    order_id: int, db: DbSession, tenant_id: CurrentTenantId
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = RequestPaymentHandler(repo)
    try:
        order = await handler.handle(RequestPaymentCommand(order_id=order_id, tenant_id=tenant_id))
        await db.commit()
        return _order_to_response(order)
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
    order_id: int, db: DbSession, tenant_id: CurrentTenantId
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = ProcessPaymentHandler(repo)
    try:
        order = await handler.handle(ProcessPaymentCommand(order_id=order_id, tenant_id=tenant_id))
        await db.commit()
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/{order_id}/cancel",
    response_model=OrderResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Cancel an active Order Form",
    dependencies=[Depends(require_permission("CLOSE_ORDER"))],
)
async def cancel_order(
    order_id: int, db: DbSession, tenant_id: CurrentTenantId
) -> OrderResponseSchema:
    repo = SQLAlchemyOrderRepository(db)
    handler = CancelOrderHandler(repo)
    try:
        order = await handler.handle(CancelOrderCommand(order_id=order_id, tenant_id=tenant_id))
        await db.commit()
        return _order_to_response(order)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


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
        return _order_to_response(order)
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
        items=[
            OrderItemResponseSchema(
                id=item.id,
                menu_item_id=item.menu_item_id,
                name_cpy=item.name_cpy,
                price_cpy=item.price_cpy.amount,
                station_type_cpy=item.station_type_cpy,
                quantity=item.quantity,
                notes=item.notes,
                subtotal=item.calculate_subtotal().amount,
                status=item.status.value,
            )
            for item in order.items
        ],
    )
