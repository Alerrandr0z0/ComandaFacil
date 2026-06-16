from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.order.domain.enums import FulfillmentStatus, OrderItemStatus
from app.order.domain.fulfillment import Delivery, Table, Takeaway
from app.order.domain.order_form import OrderForm
from app.order.domain.order_item import OrderFormItem
from app.shared.money import Money
from app.shared.value_objects import Address


def test_create_order_when_valid_params_then_initializes_with_open_state_and_empty_items() -> None:
    # Arrange
    tenant_id = "franquia_001"
    order_id = 42

    # Act
    order = OrderForm(id=order_id, tenant_id=tenant_id)

    # Assert
    assert order.id == order_id
    assert order.tenant_id == tenant_id
    assert order.items == []
    assert order.state.name == "OPEN"
    assert order.fulfillment_strategy is None


def test_add_item_when_open_state_then_appends_to_items() -> None:
    # Arrange
    order = OrderForm(id=1, tenant_id="franquia_001")
    item = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza Marguerita",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=2,
        notes="Sem cebola",
    )

    # Act
    order.add_item(item)

    # Assert
    assert len(order.items) == 1
    assert order.items[0] == item
    assert order.items[0].calculate_subtotal() == Money(Decimal("79.80"))


def test_total_calculation_includes_items_subtotal_and_fulfillment_fee() -> None:
    # Arrange
    order = OrderForm(id=1, tenant_id="franquia_001")
    item1 = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=2,
    )
    item2 = OrderFormItem(
        id=2,
        menu_item_id=11,
        name_cpy="Suco",
        price_cpy=Money(Decimal("8.50")),
        station_type_cpy="Beverage",
        quantity=1,
    )
    order.add_item(item1)
    order.add_item(item2)

    # Act & Assert - Sem estratégia (default zero fee)
    assert order.total() == Money(Decimal("88.30"))

    # Act & Assert - Com estratégia de Delivery (fee de 7.00)
    addr = Address("Rua A", "100", "Bairro X", "São Paulo", "SP", "01001-000")
    order.set_fulfillment_strategy(Delivery(address=addr))
    assert order.total() == Money(Decimal("95.30"))


def test_state_transitions_from_open_to_paid_and_closed() -> None:
    # Arrange
    order = OrderForm(id=1, tenant_id="franquia_001")
    item = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=1,
    )
    order.add_item(item)

    # Act 1: Request Payment (bloqueia comanda)
    order.request_payment()
    assert (
        order.state.name == "OPEN"
    )  # Solicitação de conta. Ainda está em aberto/processando no Postgres, mas bloqueada para novos itens no app

    # Act 2: Process Payment (muda estado para PAID)
    order.process_payment()
    assert order.state.name == "PAID"

    # Act 3: Deliver Order (muda estado para CLOSED se todos os itens entregues)
    table_strat = Table(5)
    order.set_fulfillment_strategy(table_strat)
    order.deliver()

    assert order.state.name == "CLOSED"
    assert table_strat.get_status() == FulfillmentStatus.DELIVERED


def test_add_item_when_paid_or_closed_state_then_raises_value_error() -> None:
    # Arrange
    order = OrderForm(id=1, tenant_id="franquia_001")
    item1 = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=1,
    )
    order.add_item(item1)

    # Transiciona para PAID
    order.request_payment()
    order.process_payment()

    item2 = OrderFormItem(
        id=2,
        menu_item_id=11,
        name_cpy="Suco",
        price_cpy=Money(Decimal("8.50")),
        station_type_cpy="Beverage",
        quantity=1,
    )

    # Act & Assert - Não pode adicionar no estado PAID
    with pytest.raises(ValueError, match="Cannot add items to a paid order"):
        order.add_item(item2)

    # Transiciona para CLOSED
    order.set_fulfillment_strategy(Takeaway("Alerrandro"))
    order.deliver()

    # Act & Assert - Não pode adicionar no estado CLOSED
    with pytest.raises(ValueError, match="Cannot add items to a closed order"):
        order.add_item(item2)


def test_delivery_state_transitions_when_happy_path_then_success() -> None:
    # Arrange
    addr = Address("Rua A", "100", "Bairro X", "São Paulo", "SP", "01001-000")
    delivery = Delivery(address=addr)
    assert delivery.state.name == "AWAITING_PICKUP"
    assert delivery.get_status() == FulfillmentStatus.READY_FOR_PICKUP

    # Act 1: Despachar
    delivery.dispatch()
    assert delivery.state.name == "IN_TRANSIT"
    assert delivery.get_status() == FulfillmentStatus.SHIPPED

    # Act 2: Entregar (usa stub de OrderForm pois deliver exige)
    order = OrderForm(id=1, tenant_id="franquia_001")
    delivery.deliver(order)
    assert delivery.state.name == "DELIVERED"
    assert delivery.get_status() == FulfillmentStatus.DELIVERED


def test_delivery_state_transitions_when_failure_and_retry_then_success() -> None:
    # Arrange
    addr = Address("Rua A", "100", "Bairro X", "São Paulo", "SP", "01001-000")
    delivery = Delivery(address=addr)
    order = OrderForm(id=1, tenant_id="franquia_001")

    # Act 1: Despacha e falha
    delivery.dispatch()
    delivery.fail()
    assert delivery.state.name == "FAILED_DELIVERY"
    assert delivery.get_status() == FulfillmentStatus.RETURNED

    # Act 2: Re-despacha e entrega
    delivery.dispatch()
    assert delivery.state.name == "IN_TRANSIT"
    assert delivery.get_status() == FulfillmentStatus.SHIPPED

    delivery.deliver(order)
    assert delivery.state.name == "DELIVERED"
    assert delivery.get_status() == FulfillmentStatus.DELIVERED


def test_delivery_state_transitions_when_invalid_then_raises_value_error() -> None:
    addr = Address("Rua A", "100", "Bairro X", "São Paulo", "SP", "01001-000")
    delivery = Delivery(address=addr)
    order = OrderForm(id=1, tenant_id="franquia_001")

    # AwaitingPickup -> cannot deliver or fail directly
    with pytest.raises(ValueError, match="Cannot deliver package before it is dispatched"):
        delivery.deliver(order)
    with pytest.raises(ValueError, match="Cannot fail delivery before it is dispatched"):
        delivery.fail()

    # InTransit -> cannot dispatch again
    delivery.dispatch()
    with pytest.raises(ValueError, match="Delivery is already in transit"):
        delivery.dispatch()

    # Delivered -> final state, no more transitions allowed
    delivery.deliver(order)
    with pytest.raises(
        ValueError, match="Cannot dispatch a package that has already been delivered"
    ):
        delivery.dispatch()
    with pytest.raises(ValueError, match="Package has already been delivered"):
        delivery.deliver(order)
    with pytest.raises(ValueError, match="Cannot fail a package that has already been delivered"):
        delivery.fail()


@pytest.mark.hypothesis
@given(
    quantity=st.integers(min_value=1, max_value=100),
    price_val=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000.00"), places=2),
)
def test_order_item_subtotal_property(quantity: int, price_val: Decimal) -> None:
    price = Money(price_val)
    item = OrderFormItem(
        id=1,
        menu_item_id=1,
        name_cpy="Test Item",
        price_cpy=price,
        station_type_cpy="Grill",
        quantity=quantity,
    )
    expected_subtotal = price * quantity
    assert item.calculate_subtotal() == expected_subtotal


@pytest.mark.hypothesis
@given(
    street=st.text(min_size=1).map(lambda s: s.strip()),
    number=st.text(min_size=1).map(lambda s: s.strip()),
    neighborhood=st.text(min_size=1).map(lambda s: s.strip()),
    city=st.text(min_size=1).map(lambda s: s.strip()),
    state=st.text(min_size=1).map(lambda s: s.strip()),
    postal_code=st.from_regex(r"^\d{5}-?\d{3}$"),
)
def test_address_validation_property(
    street: str, number: str, neighborhood: str, city: str, state: str, postal_code: str
) -> None:
    # Filtra campos vazios que possam ter sido causados por strip
    if not (street and number and neighborhood and city and state and postal_code):
        return
    addr = Address(
        street=street,
        number=number,
        neighborhood=neighborhood,
        city=city,
        state=state,
        postal_code=postal_code,
    )
    assert addr.street == street
    assert addr.number == number


# ─── Item Cancellation ──────────────────────────────────────────────────────────


def test_cancel_quantity_when_item_has_delivered_quantity_then_raises_value_error() -> None:
    # Arrange
    item = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=2,
        delivered_quantity=1,
    )

    # Act & Assert
    # delivered_quantity=1 of 2 → only 1 cancellable; try cancel 2 should fail
    with pytest.raises(ValueError, match="máximo permitido é 1"):
        item.cancel_quantity(2)


def test_cancel_quantity_when_status_already_canceled_then_cancellable_quantity_zero() -> None:
    # Arrange
    item = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=1,
        status=OrderItemStatus.CANCELED,
    )

    # Act & Assert
    assert item.cancellable_quantity == 0
    with pytest.raises(ValueError, match="máximo permitido é 0"):
        item.cancel_quantity(1)


def test_cancel_quantity_when_item_waiting_then_increments_canceled_quantity() -> None:
    # Arrange
    item = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=2,
    )

    # Act
    item.cancel_quantity(1)

    # Assert
    assert item.quantity == 2  # original quantity preserved
    assert item.canceled_quantity == 1
    assert item.status == OrderItemStatus.WAITING


def test_cancel_quantity_when_all_units_canceled_then_sets_status_canceled() -> None:
    # Arrange
    item = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=1,
        status=OrderItemStatus.PREPARING,
    )

    # Act
    item.cancel_quantity(1)

    # Assert
    assert item.quantity == 1  # original quantity preserved
    assert item.canceled_quantity == 1
    assert item.status == OrderItemStatus.CANCELED


def test_total_when_item_canceled_then_excludes_it() -> None:
    # Arrange
    order = OrderForm(id=1, tenant_id="franquia_001")
    item1 = OrderFormItem(
        id=1,
        menu_item_id=10,
        name_cpy="Pizza",
        price_cpy=Money(Decimal("39.90")),
        station_type_cpy="Grill",
        quantity=2,
    )
    item2 = OrderFormItem(
        id=2,
        menu_item_id=11,
        name_cpy="Suco",
        price_cpy=Money(Decimal("8.50")),
        station_type_cpy="Beverage",
        quantity=1,
    )
    order.add_item(item1)
    order.add_item(item2)

    # Act
    item2.cancel_quantity(1)

    # Assert - Suco cancelado não entra no total
    assert order.total() == Money(Decimal("79.80"))  # apenas 2x Pizza


def test_cancel_order_when_open_then_records_order_cancelled_event() -> None:
    # Arrange
    order = OrderForm(id=1, tenant_id="franquia_001")
    order.collect_events()  # Clear initial OrderCreated event

    # Act
    order.cancel()

    # Assert
    events = order.collect_events()
    assert len(events) == 1
    event = events[0]
    from app.order.domain.order_events import OrderCancelled

    assert isinstance(event, OrderCancelled)
    assert event.order_id == 1
    assert event.tenant_id == "franquia_001"
