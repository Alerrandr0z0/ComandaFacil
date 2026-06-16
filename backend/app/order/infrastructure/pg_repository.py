from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.order.domain.delivery_states import AwaitingPickup, Delivered, FailedDelivery, InTransit
from app.order.domain.enums import FulfillmentStatus, OrderItemStatus
from app.order.domain.fulfillment import Delivery, IFulfillmentStrategy, Table, Takeaway
from app.order.domain.order_events import OrderItemAdded
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.order.domain.repository import OrderRepository
from app.order.domain.states import Closed, Open, Paid
from app.order.infrastructure.orm_models import OrderFormItemORM, OrderFormORM
from app.shared.domain_events import register_pending_events
from app.shared.money import Money
from app.shared.value_objects import Address

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class SQLAlchemyOrderRepository(OrderRepository):
    """SQLAlchemy implementation of OrderRepository."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_by_id(self, id: int, tenant_id: str) -> OrderForm | None:
        stmt = (
            select(OrderFormORM)
            .where(OrderFormORM.id == id, OrderFormORM.tenant_id == tenant_id)
            .options(selectinload(OrderFormORM.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_all_by_tenant(self, tenant_id: str) -> list[OrderForm]:
        stmt = (
            select(OrderFormORM)
            .where(OrderFormORM.tenant_id == tenant_id)
            .options(selectinload(OrderFormORM.items))
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def find_by_item_id(self, item_id: int, tenant_id: str) -> OrderForm | None:
        stmt = (
            select(OrderFormORM)
            .join(OrderFormORM.items)
            .where(OrderFormItemORM.id == item_id, OrderFormORM.tenant_id == tenant_id)
            .options(selectinload(OrderFormORM.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            return None
        return self._map_to_domain(orm)

    async def find_all_active_by_tenant(self, tenant_id: str) -> list[OrderForm]:
        stmt = (
            select(OrderFormORM)
            .where(OrderFormORM.tenant_id == tenant_id, OrderFormORM.state != "CLOSED")
            .options(selectinload(OrderFormORM.items))
        )
        result = await self._session.execute(stmt)
        orms = result.scalars().all()
        return [self._map_to_domain(o) for o in orms]

    async def save(self, order: OrderForm) -> None:
        stmt = (
            select(OrderFormORM)
            .where(OrderFormORM.id == order.id, OrderFormORM.tenant_id == order.tenant_id)
            .options(selectinload(OrderFormORM.items))
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()

        if orm:
            orm.state = order.state.name
            orm.display_code = order.display_code
            orm.payment_requested = order._payment_requested  # type: ignore[reportPrivateUsage]
            orm.items.clear()
        else:
            orm_kwargs = {
                "tenant_id": order.tenant_id,
                "display_code": order.display_code,
                "state": order.state.name,
                "payment_requested": order._payment_requested,  # type: ignore[reportPrivateUsage]
                "created_at": order.created_at,
            }
            if order.id != 0:
                orm_kwargs["id"] = order.id
                
            orm = OrderFormORM(**orm_kwargs)
            self._session.add(orm)

        # Map fulfillment strategy fields
        self._map_strategy_to_orm(orm, order.fulfillment_strategy)

        # Re-populate items
        new_item_orms: list[OrderFormItemORM] = []
        newly_created_map: dict[tuple[int, str], int] = {}
        for item in order.items:
            is_new = item.id == 0
            item_kwargs: dict[str, object] = {
                "order_id": order.id,
                "menu_item_id": item.menu_item_id,
                "name_cpy": item.name_cpy,
                "price_cpy": item.price_cpy.amount,
                "station_type_cpy": item.station_type_cpy,
                "quantity": item.quantity,
                "delivered_quantity": item.delivered_quantity,
                "canceled_quantity": item.canceled_quantity,
                "notes": item.notes,
                "status": item.status.value,
            }
            if not is_new:
                item_kwargs["id"] = item.id
            item_orm = OrderFormItemORM(**item_kwargs)
            orm.items.append(item_orm)
            new_item_orms.append(item_orm)

        await self._session.flush()
        
        # Update domain order ID if it was auto-generated
        if order.id == 0:
            order.id = orm.id
            if order.display_code == "0":
                order.display_code = str(orm.id)
                orm.display_code = order.display_code

        # Update domain item IDs from auto-generated ORM IDs
        for domain_item, item_orm in zip(order.items, new_item_orms, strict=True):
            if domain_item.id == 0:
                domain_item.id = item_orm.id
                newly_created_map[(domain_item.menu_item_id, domain_item.notes or "")] = item_orm.id

        # Map auto-generated IDs onto OrderItemAdded domain events
        raw_events = order.collect_events()
        processed_events = []
        for ev in raw_events:
            event_to_add = ev
            if isinstance(ev, OrderItemAdded) and ev.item_id == 0:
                key = (ev.menu_item_id, ev.notes or "")
                new_id = newly_created_map.get(key)
                if new_id is not None:
                    event_to_add = OrderItemAdded(
                        order_id=ev.order_id,
                        tenant_id=ev.tenant_id,
                        item_id=new_id,
                        menu_item_id=ev.menu_item_id,
                        name=ev.name,
                        quantity=ev.quantity,
                        price=ev.price,
                        notes=ev.notes,
                        occurred_at=ev.occurred_at,
                    )
            processed_events.append(event_to_add)

        register_pending_events(processed_events)

    async def delete(self, id: int, tenant_id: str) -> None:
        stmt = select(OrderFormORM).where(
            OrderFormORM.id == id, OrderFormORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    def _map_strategy_to_orm(self, orm: OrderFormORM, strat: IFulfillmentStrategy | None) -> None:
        """Helper to map fulfillment strategy to ORM fields."""
        if strat is None:
            orm.fulfillment_type = None
            orm.table_number = None
            orm.customer_name = None
            self._clear_delivery_orm_fields(orm)
        elif isinstance(strat, Table):
            orm.fulfillment_type = "TABLE"
            orm.table_number = strat.table_num
            orm.customer_name = None
            self._clear_delivery_orm_fields(orm)
        elif isinstance(strat, Takeaway):
            orm.fulfillment_type = "TAKEAWAY"
            orm.table_number = None
            orm.customer_name = strat.customer_name
            self._clear_delivery_orm_fields(orm)
        elif isinstance(strat, Delivery):
            orm.fulfillment_type = "DELIVERY"
            orm.table_number = None
            orm.customer_name = None
            orm.delivery_street = strat.address.street
            orm.delivery_number = strat.address.number
            orm.delivery_neighborhood = strat.address.neighborhood
            orm.delivery_city = strat.address.city
            orm.delivery_state = strat.address.state
            orm.delivery_postal_code = strat.address.postal_code
            orm.delivery_estimated_time = strat.estimated_time
            orm.delivery_tracking_code = strat.tracking_code
            orm.delivery_state_name = strat.state.name

    def _clear_delivery_orm_fields(self, orm: OrderFormORM) -> None:
        """Clears all delivery-related ORM fields."""
        orm.delivery_street = None
        orm.delivery_number = None
        orm.delivery_neighborhood = None
        orm.delivery_city = None
        orm.delivery_state = None
        orm.delivery_postal_code = None
        orm.delivery_estimated_time = None
        orm.delivery_tracking_code = None
        orm.delivery_state_name = None

    def _map_to_domain(self, orm: OrderFormORM) -> OrderForm:
        order = OrderForm(
            id=orm.id,
            tenant_id=orm.tenant_id,
            display_code=orm.display_code,
            created_at=orm.created_at,
        )
        order._payment_requested = orm.payment_requested  # type: ignore[reportPrivateUsage]

        # Map state
        if orm.state == "OPEN":
            order._state = Open()  # type: ignore[reportPrivateUsage]
        elif orm.state == "PAID":
            order._state = Paid()  # type: ignore[reportPrivateUsage]
        elif orm.state == "CLOSED":
            order._state = Closed()  # type: ignore[reportPrivateUsage]

        # Map strategy
        order.fulfillment_strategy = self._map_strategy_to_domain(orm)

        # Populate items
        for item_orm in orm.items:
            item = OrderFormItem(
                id=item_orm.id,
                menu_item_id=item_orm.menu_item_id,
                name_cpy=item_orm.name_cpy,
                price_cpy=Money(item_orm.price_cpy),
                station_type_cpy=item_orm.station_type_cpy,
                quantity=item_orm.quantity,
                delivered_quantity=item_orm.delivered_quantity,
                canceled_quantity=item_orm.canceled_quantity,
                notes=item_orm.notes or "",
                status=OrderItemStatus(item_orm.status),
            )
            order._items.append(item)  # type: ignore[reportPrivateUsage]

        return order

    def _map_strategy_to_domain(self, orm: OrderFormORM) -> IFulfillmentStrategy | None:
        """Helper to reconstruct fulfillment strategy from ORM."""
        if orm.fulfillment_type == "TABLE":
            assert orm.table_number is not None
            table = Table(orm.table_number)
            if orm.state == "CLOSED":
                table._status = FulfillmentStatus.DELIVERED  # type: ignore[reportPrivateUsage]
            return table

        if orm.fulfillment_type == "TAKEAWAY":
            assert orm.customer_name is not None
            takeaway = Takeaway(orm.customer_name)
            if orm.state == "CLOSED":
                takeaway._status = FulfillmentStatus.DELIVERED  # type: ignore[reportPrivateUsage]
            return takeaway

        if orm.fulfillment_type == "DELIVERY":
            return self._map_delivery_to_domain(orm)

        return None

    def _map_delivery_to_domain(self, orm: OrderFormORM) -> Delivery:
        """Helper to reconstruct delivery strategy from ORM."""
        assert orm.delivery_street is not None
        assert orm.delivery_number is not None
        assert orm.delivery_neighborhood is not None
        assert orm.delivery_city is not None
        assert orm.delivery_state is not None
        assert orm.delivery_postal_code is not None
        assert orm.delivery_estimated_time is not None
        assert orm.delivery_tracking_code is not None

        addr = Address(
            street=orm.delivery_street,
            number=orm.delivery_number,
            neighborhood=orm.delivery_neighborhood,
            city=orm.delivery_city,
            state=orm.delivery_state,
            postal_code=orm.delivery_postal_code,
        )
        delivery = Delivery(
            address=addr,
            estimated_time=orm.delivery_estimated_time,
            tracking_code=orm.delivery_tracking_code,
        )

        # Reconstruct delivery state and status
        if orm.delivery_state_name == "AWAITING_PICKUP":
            delivery._state = AwaitingPickup()  # type: ignore[reportPrivateUsage]
        elif orm.delivery_state_name == "IN_TRANSIT":
            delivery._state = InTransit()  # type: ignore[reportPrivateUsage]
        elif orm.delivery_state_name == "DELIVERED":
            delivery._state = Delivered()  # type: ignore[reportPrivateUsage]
        elif orm.delivery_state_name == "FAILED_DELIVERY":
            delivery._state = FailedDelivery()  # type: ignore[reportPrivateUsage]

        return delivery
