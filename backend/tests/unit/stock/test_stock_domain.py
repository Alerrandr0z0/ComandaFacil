from __future__ import annotations

from decimal import Decimal

from app.shared.value_objects import MeasuredQuantity
from app.stock.domain.converters import MetricConverter
from app.stock.domain.enums import TransactionType
from app.stock.domain.recipe import Recipe
from app.stock.domain.stock_item import CompositeStockItem, SimpleStockItem
from app.stock.domain.transaction import StockTransaction


def test_measured_quantity_conversions() -> None:
    qty_g = MeasuredQuantity(Decimal("1500"), "g")
    qty_kg = qty_g.convert_to("kg", MetricConverter())
    assert qty_kg.value == Decimal("1.5")
    assert qty_kg.unit == "kg"

    qty_l = MeasuredQuantity(Decimal("2.5"), "l")
    qty_ml = qty_l.convert_to("ml", MetricConverter())
    assert qty_ml.value == Decimal("2500")
    assert qty_ml.unit == "ml"


def test_measured_quantity_arithmetic_same_unit() -> None:
    q1 = MeasuredQuantity(Decimal("10"), "kg")
    q2 = MeasuredQuantity(Decimal("5"), "kg")
    added = q1.add(q2)
    assert added.value == Decimal("15")
    assert added.unit == "kg"

    subtracted = q1.subtract(q2)
    assert subtracted.value == Decimal("5")
    assert subtracted.unit == "kg"


def test_measured_quantity_arithmetic_different_unit() -> None:
    q1 = MeasuredQuantity(Decimal("1"), "kg")
    q2 = MeasuredQuantity(Decimal("500"), "g")

    # Adding g to kg
    res_add = q1.add(q2)
    assert res_add.value == Decimal("1.5")
    assert res_add.unit == "kg"

    # Subtracting g from kg
    res_sub = q1.subtract(q2)
    assert res_sub.value == Decimal("0.5")
    assert res_sub.unit == "kg"


def test_simple_stock_item_ledger_balance() -> None:
    item = SimpleStockItem(
        id=1,
        tenant_id="t1",
        name="Tomate",
        category="RAW_MATERIAL",
        unit="kg",
        min_stock_level=5.0,
    )
    assert item.get_balance().value == Decimal("0")

    # Add INPUT transaction
    item.add_transaction(
        StockTransaction(
            id=1, quantity=MeasuredQuantity(Decimal("10"), "kg"), type=TransactionType.INPUT
        )
    )
    assert item.get_balance().value == Decimal("10")

    # Add OUTPUT transaction
    item.add_transaction(
        StockTransaction(
            id=2, quantity=MeasuredQuantity(Decimal("3"), "kg"), type=TransactionType.OUTPUT
        )
    )
    assert item.get_balance().value == Decimal("7")

    # Add ADJUSTMENT transaction (sets to 5)
    item.add_transaction(
        StockTransaction(
            id=3, quantity=MeasuredQuantity(Decimal("5"), "kg"), type=TransactionType.ADJUSTMENT
        )
    )
    assert item.get_balance().value == Decimal("5")

    # Subsequent OUTPUT transaction (5 - 2 = 3)
    item.add_transaction(
        StockTransaction(
            id=4, quantity=MeasuredQuantity(Decimal("2"), "kg"), type=TransactionType.OUTPUT
        )
    )
    assert item.get_balance().value == Decimal("3")
    assert item.is_low_stock is True


def test_composite_stock_item_balance() -> None:
    # Components
    c1 = SimpleStockItem(1, "t1", "Hambúrguer de Carne", "RAW_MATERIAL", "un")
    c1.add_transaction(
        StockTransaction(1, MeasuredQuantity(Decimal("10"), "un"), TransactionType.INPUT)
    )

    c2 = SimpleStockItem(2, "t1", "Pão de Hambúrguer", "RAW_MATERIAL", "un")
    c2.add_transaction(
        StockTransaction(1, MeasuredQuantity(Decimal("8"), "un"), TransactionType.INPUT)
    )

    composite = CompositeStockItem(
        id=3,
        tenant_id="t1",
        name="Hamburguer Duplo",
        category="RAW_MATERIAL",
        unit="un",
    )
    composite.add_component(c1)
    composite.add_component(c2)

    # Combined balance = 10 + 8 = 18
    assert composite.get_balance().value == Decimal("18")


def test_recipe_ingredients() -> None:
    item = SimpleStockItem(1, "t1", "Carne", "RAW_MATERIAL", "kg")
    recipe = Recipe(id=1, menu_item_id=101, tenant_id="t1")
    recipe.add_ingredient(item, MeasuredQuantity(Decimal("0.150"), "kg"))

    ingredients = recipe.get_ingredients()
    assert len(ingredients) == 1
    assert ingredients[0].stock_item.id == 1
    assert ingredients[0].quantity.value == Decimal("0.150")
