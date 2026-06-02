from __future__ import annotations

import pytest

from app.shared.exceptions import InsufficientStockError
from app.shared.value_objects import MeasuredQuantity, MeasurementUnit
from app.stock.domain.enums import MovementType
from app.stock.domain.stock_item import StockItem
from app.stock.domain.stock_movement import StockMovement


def test_create_stock_item_when_valid_params_then_initializes() -> None:
    # Arrange
    qty = MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM)

    # Act
    item = StockItem(
        id=1,
        tenant_id="franquia_001",
        name="Farinha de Trigo",
        category="RAW_MATERIAL",
        current_quantity=qty,
        min_stock_level=5.0,
    )

    # Assert
    assert item.id == 1
    assert item.tenant_id == "franquia_001"
    assert item.name == "Farinha de Trigo"
    assert item.category == "RAW_MATERIAL"
    assert item.current_quantity == qty
    assert item.min_stock_level == 5.0
    assert item.is_active is True


def test_add_stock_when_positive_quantity_then_increases() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(5.0, MeasurementUnit.KILOGRAM),
    )

    # Act
    item.add_stock(3.0)

    # Assert
    assert item.current_quantity.amount == 8.0


def test_add_stock_when_zero_or_negative_then_raises() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(5.0, MeasurementUnit.KILOGRAM),
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Quantity to add must be positive"):
        item.add_stock(0)

    with pytest.raises(ValueError, match="Quantity to add must be positive"):
        item.add_stock(-1)


def test_deduct_stock_when_sufficient_then_decreases() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM),
    )

    # Act
    item.deduct_stock(4.0)

    # Assert
    assert item.current_quantity.amount == 6.0


def test_deduct_stock_when_insufficient_then_raises() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(2.0, MeasurementUnit.KILOGRAM),
    )

    # Act & Assert
    with pytest.raises(InsufficientStockError):
        item.deduct_stock(5.0)


def test_deduct_stock_when_zero_or_negative_then_raises() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(5.0, MeasurementUnit.KILOGRAM),
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Quantity to deduct must be positive"):
        item.deduct_stock(0)

    with pytest.raises(ValueError, match="Quantity to deduct must be positive"):
        item.deduct_stock(-3)


def test_adjust_stock_when_valid_then_sets_exact_quantity() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM),
    )

    # Act
    item.adjust_stock(7.5)

    # Assert
    assert item.current_quantity.amount == 7.5


def test_adjust_stock_when_negative_then_raises() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(5.0, MeasurementUnit.KILOGRAM),
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Quantity cannot be negative"):
        item.adjust_stock(-1)


def test_set_min_stock_level_when_valid_then_updates() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM),
    )

    # Act
    item.set_min_stock_level(8.0)

    # Assert
    assert item.min_stock_level == 8.0


def test_set_min_stock_level_when_negative_then_raises() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(10.0, MeasurementUnit.KILOGRAM),
    )

    # Act & Assert
    with pytest.raises(ValueError, match="Minimum stock level cannot be negative"):
        item.set_min_stock_level(-1)


def test_is_low_stock_when_below_min_then_returns_true() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(3.0, MeasurementUnit.KILOGRAM),
        min_stock_level=5.0,
    )

    # Assert
    assert item.is_low_stock is True


def test_is_low_stock_when_above_min_then_returns_false() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(7.0, MeasurementUnit.KILOGRAM),
        min_stock_level=5.0,
    )

    # Assert
    assert item.is_low_stock is False


def test_activate_and_deactivate() -> None:
    # Arrange
    item = StockItem(
        1, "t1", "Tomate", "RAW_MATERIAL",
        MeasuredQuantity(5.0, MeasurementUnit.KILOGRAM),
    )
    assert item.is_active is True

    # Act
    item.deactivate()

    # Assert
    assert item.is_active is False

    # Act
    item.activate()

    # Assert
    assert item.is_active is True


def test_stock_movement_value_object() -> None:
    # Act
    movement = StockMovement(
        id=1,
        stock_item_id=1,
        movement_type=MovementType.INBOUND,
        quantity_changed=10.0,
        reason="Initial stock",
    )

    # Assert
    assert movement.id == 1
    assert movement.stock_item_id == 1
    assert movement.movement_type == MovementType.INBOUND
    assert movement.quantity_changed == 10.0
    assert movement.reason == "Initial stock"
    assert movement.reference_type is None
    assert movement.reference_id is None
