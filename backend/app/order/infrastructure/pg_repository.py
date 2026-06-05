from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.order.domain.delivery_states import AwaitingPickup, Delivered, FailedDelivery, InTransit
from app.order.domain.enums import FulfillmentStatus
from app.order.domain.fulfillment import Delivery, IFulfillmentStratrgy, Table, Takeaway
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.order.domain.repository import OrderRepository
from app.order.domain.states import Closed, Open, Paid
from app.order.infrastructure.orm_models import OrderFormItemORM, OrderFormORM
from app.shared.money import Money
from app.shared.value_objects import Address, TableNum

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
            orm.payment_requested = order._payment_requested  # type: ignore[reportPrivateUsage]
            orm.items.clear()
        else:
            orm = OrderFormORM(
                id=order.id,
                tenant_id=order.tenant_id,
                state=order.state.name,
                payment_requested=order._payment_requested,  # type: ignore[reportPrivateUsage]
            )
            self._session.add(orm)

        # Map fulfillment strategy fields
        self._map_strategy_to_orm(orm, order.fulfillment_strategy)

        # Re-populate items
        for item in order.items:
            item_orm = OrderFormItemORM(
                id=item.id,
                order_id=order.id,
                menu_item_id=item.menu_item_id,
                name_cpy=item.name_cpy,
                price_cpy=item.price_cpy.amount,
                station_type_cpy=item.station_type_cpy,
                quantity=item.quantity,
                notes=item.notes,
            )
            orm.items.append(item_orm)

        await self._session.flush()

    async def delete(self, id: int, tenant_id: str) -> None:
        stmt = select(OrderFormORM).where(
            OrderFormORM.id == id, OrderFormORM.tenant_id == tenant_id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self._session.delete(orm)
            await self._session.flush()

    def _map_strategy_to_orm(self, orm: OrderFormORM, strat: IFulfillmentStratrgy | None) -> None:
        """Helper to map fulfillment strategy to ORM fields."""
        if strat is None:
            orm.fulfillment_type = None
            orm.table_number = None
            orm.customer_name = None
            self._clear_delivery_orm_fields(orm)
        elif isinstance(strat, Table):
            orm.fulfillment_type = "TABLE"
            orm.table_number = strat.table_num.value
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
        order = OrderForm(id=orm.id, tenant_id=orm.tenant_id)
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
                notes=item_orm.notes or "",
            )
            order._items.append(item)  # type: ignore[reportPrivateUsage]

        return order

    def _map_strategy_to_domain(self, orm: OrderFormORM) -> IFulfillmentStratrgy | None:
        """Helper to reconstruct fulfillment strategy from ORM."""
        if orm.fulfillment_type == "TABLE":
            assert orm.table_number is not None
            table = Table(TableNum(orm.table_number))
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
            delivery._status = FulfillmentStatus.READY_FOR_PICKUP  # type: ignore[reportPrivateUsage]
        elif orm.delivery_state_name == "IN_TRANSIT":
            delivery._state = InTransit()  # type: ignore[reportPrivateUsage]
            delivery._status = FulfillmentStatus.SHIPPED  # type: ignore[reportPrivateUsage]
        elif orm.delivery_state_name == "DELIVERED":
            delivery._state = Delivered()  # type: ignore[reportPrivateUsage]
            delivery._status = FulfillmentStatus.DELIVERED  # type: ignore[reportPrivateUsage]
        elif orm.delivery_state_name == "FAILED_DELIVERY":
            delivery._state = FailedDelivery()  # type: ignore[reportPrivateUsage]
            delivery._status = FulfillmentStatus.RETURNED  # type: ignore[reportPrivateUsage]

        return delivery
