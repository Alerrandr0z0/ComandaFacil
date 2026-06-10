from __future__ import annotations

import pytest

from app.kitchen.domain.kitchen_item import KitchenOrderItem
from app.kitchen.domain.kitchen_station import Beverage, Grill


def test_create_kitchen_item_when_valid_params_then_initializes_with_waiting_state() -> None:
    # Arrange
    item_id = 1
    correlation_id = 42
    name = "Burguer"
    station = "Grill"
    tenant = "franquia_001"

    # Act
    item = KitchenOrderItem(
        id=item_id,
        correlation_id=correlation_id,
        name_cpy=name,
        station_type_cpy=station,
        tenant_id=tenant,
    )

    # Assert
    assert item.id == item_id
    assert item.correlation_id == correlation_id
    assert item.name_cpy == name
    assert item.station_type_cpy == station
    assert item.tenant_id == tenant
    assert item.state.name == "WAITING"


def test_kitchen_item_prepare_when_waiting_then_transitions_to_preparing() -> None:
    # Arrange
    item = KitchenOrderItem(1, 42, "Burguer", "Grill", "franquia_001")

    # Act
    item.prepare()

    # Assert
    assert item.state.name == "PREPARING"


def test_kitchen_item_ready_when_preparing_then_transitions_to_ready() -> None:
    # Arrange
    item = KitchenOrderItem(1, 42, "Burguer", "Grill", "franquia_001")
    item.prepare()

    # Act
    item.mark_as_ready()

    # Assert
    assert item.state.name == "READY"


def test_kitchen_item_cancel_when_waiting_or_preparing_then_transitions_to_cancelled() -> None:
    # Arrange 1: cancel from waiting
    item1 = KitchenOrderItem(1, 42, "Burguer", "Grill", "franquia_001")
    item1.cancel()
    assert item1.state.name == "CANCELLED"

    # Arrange 2: cancel from preparing
    item2 = KitchenOrderItem(2, 43, "Burguer", "Grill", "franquia_001")
    item2.prepare()
    item2.cancel()
    assert item2.state.name == "CANCELLED"


def test_kitchen_item_invalid_transitions_then_raises_value_error() -> None:
    # Arrange
    item = KitchenOrderItem(1, 42, "Burguer", "Grill", "franquia_001")

    # Act & Assert 1: cannot mark ready from waiting (STANDARD profile requires PREPARING first)
    with pytest.raises(ValueError, match="Item requires preparation"):
        item.mark_as_ready()

    # Act & Assert 2: cannot prepare from preparing
    item.prepare()
    with pytest.raises(ValueError, match="Item is already being prepared"):
        item.prepare()

    # Act & Assert 3: cannot prepare or cancel from ready
    item.mark_as_ready()
    with pytest.raises(ValueError, match="Cannot prepare a ready item"):
        item.prepare()
    with pytest.raises(ValueError, match="Cannot cancel a ready item"):
        item.cancel()


def test_kitchen_stations_creation_and_inheritance() -> None:
    # Arrange
    grill = Grill(id=1, tenant_id="franquia_001", is_active=True)
    bev = Beverage(id=2, tenant_id="franquia_001", is_active=True)

    # Assert
    assert grill.id == 1
    assert grill.station_type == "GRILL"
    assert grill.is_active is True

    assert bev.id == 2
    assert bev.station_type == "BEVERAGE"
    assert bev.is_active is True
