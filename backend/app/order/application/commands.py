from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal  # noqa: TC003
from typing import TYPE_CHECKING, Final

from app.order.domain.fulfillment import Delivery, Table, Takeaway
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.shared.exceptions import ConflictError, NotFoundError
from app.shared.money import Money
from app.shared.value_objects import Address

if TYPE_CHECKING:
    from app.order.domain.repository import OrderRepository
    from app.order.infrastructure.mongo_repository import OrderHistoryMongoRepository


@dataclass(frozen=True)
class CreateOrderCommand:
    tenant_id: str
    fulfillment_type: str
    id: int | None = None
    display_code: str | None = None
    table_number: int | None = None
    customer_name: str | None = None
    delivery_street: str | None = None
    delivery_number: str | None = None
    delivery_neighborhood: str | None = None
    delivery_city: str | None = None
    delivery_state: str | None = None
    delivery_postal_code: str | None = None
    delivery_estimated_time: int = 40
    delivery_tracking_code: int = 0

    def __repr__(self) -> str:
        return f"CreateOrderCommand(id={self.id}, tenant_id={self.tenant_id!r}, type={self.fulfillment_type!r})"


class CreateOrderHandler:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo: Final[OrderRepository] = order_repo

    def _generate_order_id(self, all_orders: list[OrderForm], requested_id: int | None) -> int:
        return (
            requested_id
            if requested_id is not None
            else (max((o.id for o in all_orders), default=0) + 1)
        )

    def _build_fulfillment(self, command: CreateOrderCommand, order: OrderForm) -> None:
        if command.fulfillment_type == "TABLE":
            if command.table_number is None:
                raise ValueError("Table number is required for Table strategy.")
            order.set_fulfillment_strategy(Table(command.table_number))
        elif command.fulfillment_type == "TAKEAWAY":
            if command.customer_name is None:
                raise ValueError("Customer name is required for Takeaway strategy.")
            order.set_fulfillment_strategy(Takeaway(command.customer_name))
        elif command.fulfillment_type == "DELIVERY":
            if not (
                command.delivery_street
                and command.delivery_number
                and command.delivery_neighborhood
                and command.delivery_city
                and command.delivery_state
                and command.delivery_postal_code
            ):
                raise ValueError("Full address fields are required for Delivery strategy.")
            addr = Address(
                street=command.delivery_street,
                number=command.delivery_number,
                neighborhood=command.delivery_neighborhood,
                city=command.delivery_city,
                state=command.delivery_state,
                postal_code=command.delivery_postal_code,
            )
            order.set_fulfillment_strategy(
                Delivery(
                    address=addr,
                    estimated_time=command.delivery_estimated_time,
                    tracking_code=command.delivery_tracking_code,
                )
            )
        else:
            raise ValueError(f"Fulfillment type '{command.fulfillment_type}' inválido.")

    async def handle(self, command: CreateOrderCommand) -> OrderForm:
        all_tenant_orders = await self._order_repo.find_all_by_tenant(command.tenant_id)
        order_id = self._generate_order_id(all_tenant_orders, command.id)
        existing = await self._order_repo.find_by_id(order_id, command.tenant_id)
        if existing:
            if existing.state.name == "CLOSED":
                await self._order_repo.delete(order_id, command.tenant_id)
            else:
                raise ConflictError(f"Comanda com id {order_id} já existe.")

        order = OrderForm(
            id=order_id,
            tenant_id=command.tenant_id,
            display_code=command.display_code or str(order_id),
        )
        self._build_fulfillment(command, order)
        await self._order_repo.save(order)
        return order

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class AddOrderItemCommand:
    order_id: int
    tenant_id: str
    item_id: int
    menu_item_id: int
    name_cpy: str
    price_cpy: Decimal
    station_type_cpy: str
    quantity: int
    notes: str = ""

    def __repr__(self) -> str:
        return f"AddOrderItemCommand(order_id={self.order_id}, tenant_id={self.tenant_id!r}, item_id={self.item_id}, name={self.name_cpy!r})"


class AddOrderItemHandler:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo: Final[OrderRepository] = order_repo

    async def handle(self, command: AddOrderItemCommand) -> OrderFormItem:
        order = await self._order_repo.find_by_id(command.order_id, command.tenant_id)
        if not order:
            raise NotFoundError("Comanda", command.order_id)

        item = OrderFormItem(
            id=command.item_id,
            menu_item_id=command.menu_item_id,
            name_cpy=command.name_cpy,
            price_cpy=Money(command.price_cpy),
            station_type_cpy=command.station_type_cpy,
            quantity=command.quantity,
            notes=command.notes,
        )
        order.add_item(item)
        await self._order_repo.save(order)
        return item

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class RequestPaymentCommand:
    order_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"RequestPaymentCommand(order_id={self.order_id}, tenant_id={self.tenant_id!r})"


class RequestPaymentHandler:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo: Final[OrderRepository] = order_repo

    async def handle(self, command: RequestPaymentCommand) -> OrderForm:
        order = await self._order_repo.find_by_id(command.order_id, command.tenant_id)
        if not order:
            raise NotFoundError("Comanda", command.order_id)

        order.request_payment()
        await self._order_repo.save(order)
        return order

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class ProcessPaymentCommand:
    order_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"ProcessPaymentCommand(order_id={self.order_id}, tenant_id={self.tenant_id!r})"


class ProcessPaymentHandler:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo: Final[OrderRepository] = order_repo

    async def handle(self, command: ProcessPaymentCommand) -> OrderForm:
        order = await self._order_repo.find_by_id(command.order_id, command.tenant_id)
        if not order:
            raise NotFoundError("Comanda", command.order_id)

        order.process_payment()
        await self._order_repo.save(order)
        return order

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class CancelOrderCommand:
    order_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"CancelOrderCommand(order_id={self.order_id}, tenant_id={self.tenant_id!r})"


class CancelOrderHandler:
    def __init__(self, order_repo: OrderRepository) -> None:
        self._order_repo: Final[OrderRepository] = order_repo

    async def handle(self, command: CancelOrderCommand) -> OrderForm:
        order = await self._order_repo.find_by_id(command.order_id, command.tenant_id)
        if not order:
            raise NotFoundError("Comanda", command.order_id)

        order.cancel()
        await self._order_repo.save(order)
        return order

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


@dataclass(frozen=True)
class DeliverOrderCommand:
    order_id: int
    tenant_id: str

    def __repr__(self) -> str:
        return f"DeliverOrderCommand(order_id={self.order_id}, tenant_id={self.tenant_id!r})"


class DeliverOrderHandler:
    def __init__(
        self, order_repo: OrderRepository, mongo_repo: OrderHistoryMongoRepository
    ) -> None:
        self._order_repo: Final[OrderRepository] = order_repo
        self._mongo_repo: Final[OrderHistoryMongoRepository] = mongo_repo

    async def handle(self, command: DeliverOrderCommand) -> OrderForm:
        order = await self._order_repo.find_by_id(command.order_id, command.tenant_id)
        if not order:
            raise NotFoundError("Comanda", command.order_id)

        # Re-dispatch delivery package if it's delivery strategy in failed status
        # and we want to try again (standard physical workflow tracking support)
        strat = order.fulfillment_strategy
        if isinstance(strat, Delivery) and strat.state.name == "FAILED_DELIVERY":
            strat.dispatch()

        order.deliver()
        await self._order_repo.save(order)

        # Sync/save desnormalised read model to MongoDB
        await self._mongo_repo.save(order)
        return order

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"
