from __future__ import annotations

from decimal import Decimal

from app.stock.domain.converters import MetricConverter
from app.stock.domain.enums import TransactionType
from app.stock.domain.measured_quantity import MeasuredQuantity
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
            id=1,
            quantity=MeasuredQuantity(Decimal("10"), "kg"),
            type=TransactionType.INPUT,
            cost_amount=Decimal("5.00"),
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
        StockTransaction(
            1,
            MeasuredQuantity(Decimal("10"), "un"),
            TransactionType.INPUT,
            cost_amount=Decimal("4.00"),
        )
    )

    c2 = SimpleStockItem(2, "t1", "Pão de Hambúrguer", "RAW_MATERIAL", "un")
    c2.add_transaction(
        StockTransaction(
            1,
            MeasuredQuantity(Decimal("8"), "un"),
            TransactionType.INPUT,
            cost_amount=Decimal("1.50"),
        )
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


def test_imperial_converter() -> None:
    import pytest

    from app.stock.domain.converters import ImperialConverter

    conv = ImperialConverter()
    qty_lb = MeasuredQuantity(Decimal("2"), "lb")
    qty_oz = qty_lb.convert_to("oz", conv)
    assert qty_oz.value == Decimal("32")
    assert qty_oz.unit == "oz"

    qty_oz2 = MeasuredQuantity(Decimal("8"), "oz")
    qty_lb2 = qty_oz2.convert_to("lb", conv)
    assert qty_lb2.value == Decimal("0.5")
    assert qty_lb2.unit == "lb"

    # Test conversion to same unit
    assert conv.convert(Decimal("10"), "oz", "oz") == Decimal("10")
    assert conv.convert(Decimal("5"), "fl_oz", "fl_oz") == Decimal("5")

    # Test ValueError for invalid conversion
    with pytest.raises(ValueError, match="Cannot convert"):
        conv.convert(Decimal("10"), "oz", "ml")


def test_metric_converter_edge_cases() -> None:
    import pytest

    conv = MetricConverter()
    # Test conversion to same unit
    assert conv.convert(Decimal("10"), "kg", "kg") == Decimal("10")

    # Test ValueError for invalid conversion
    with pytest.raises(ValueError, match="Cannot convert"):
        conv.convert(Decimal("10"), "kg", "ml")


def test_measured_quantity_edge_cases() -> None:
    import pytest

    # 1. Non-Decimal initialization (casting float/string to Decimal)
    q_float = MeasuredQuantity(15.5, "kg")  # type: ignore[arg-type]
    assert isinstance(q_float.value, Decimal)
    assert q_float.value == Decimal("15.5")

    # 2. Negative quantity raises ValueError
    with pytest.raises(ValueError, match="Quantidade não pode ser negativa"):
        MeasuredQuantity(Decimal("-5"), "kg")

    # 3. add() falling back to ImperialConverter when MetricConverter fails
    q_metric = MeasuredQuantity(Decimal("2"), "lb")
    q_imperial = MeasuredQuantity(Decimal("16"), "oz")
    # lb + oz. oz is not in MetricConverter, so MetricConverter raises ValueError,
    # then it falls back to ImperialConverter and succeeds
    res_add = q_metric.add(q_imperial)
    assert res_add.value == Decimal("3")
    assert res_add.unit == "lb"

    # 4. subtract() falling back to ImperialConverter when MetricConverter fails
    res_sub = q_metric.subtract(q_imperial)
    assert res_sub.value == Decimal("1")
    assert res_sub.unit == "lb"

    # 5. String representation
    assert str(q_metric) == "2lb"


def test_stock_item_edge_cases() -> None:
    import pytest

    # 1. activate and deactivate
    item = SimpleStockItem(1, "t1", "Item test", "RAW_MATERIAL", "un", is_active=True)
    item.deactivate()
    assert item.is_active is False
    item.activate()
    assert item.is_active is True

    # 2. set_min_stock_level ValueError
    with pytest.raises(ValueError, match="Minimum stock level cannot be negative"):
        item.set_min_stock_level(-10.0)

    # 3. __repr__
    rep = repr(item)
    assert "SimpleStockItem" in rep
    assert "Item test" in rep

    # 4. get_unit_cost when no input transactions
    assert item.get_unit_cost() == Decimal("0.0")

    # 5. get_unit_cost when total quantity <= 0
    from app.stock.domain.enums import TransactionType
    from app.stock.domain.transaction import StockTransaction

    item.add_transaction(
        StockTransaction(
            id=1,
            quantity=MeasuredQuantity(Decimal("0.0"), "un"),
            type=TransactionType.INPUT,
            cost_amount=Decimal("5.00"),
        )
    )
    assert item.get_unit_cost() == Decimal("0.0")

    # 6. CompositeStockItem add_transaction raises ValueError
    comp = CompositeStockItem(2, "t1", "Comp test", "RAW_MATERIAL", "un")
    with pytest.raises(ValueError, match="Transações diretas não são permitidas"):
        comp.add_transaction(
            StockTransaction(
                id=1,
                quantity=MeasuredQuantity(Decimal("10"), "un"),
                type=TransactionType.INPUT,
                cost_amount=Decimal("1.00"),
            )
        )

    # 7. CompositeStockItem get_unit_cost sums children costs
    c1 = SimpleStockItem(3, "t1", "Child 1", "RAW_MATERIAL", "un")
    c1.add_transaction(
        StockTransaction(
            id=1,
            quantity=MeasuredQuantity(Decimal("2"), "un"),
            type=TransactionType.INPUT,
            cost_amount=Decimal("4.00"),
        )
    )
    comp.add_component(c1)
    assert comp.get_unit_cost() == Decimal("4.00")


def test_recipe_edge_cases() -> None:
    from app.stock.domain.recipe import Recipe, RecipeIngredient

    # 1. repr for RecipeIngredient and Recipe
    item = SimpleStockItem(1, "t1", "Carne", "RAW_MATERIAL", "kg")
    ing = RecipeIngredient(item, MeasuredQuantity(Decimal("0.150"), "kg"))
    assert "RecipeIngredient" in repr(ing)

    recipe = Recipe(id=1, menu_item_id=101, tenant_id="t1")
    recipe.add_ingredient(item, MeasuredQuantity(Decimal("0.150"), "kg"))
    assert "Recipe" in repr(recipe)

    # 2. Duplicate ingredient in add_ingredient updates quantity
    recipe.add_ingredient(item, MeasuredQuantity(Decimal("0.300"), "kg"))
    ingredients = recipe.get_ingredients()
    assert len(ingredients) == 1
    assert ingredients[0].quantity.value == Decimal("0.300")

    # 3. calculate_total_cost
    item.get_unit_cost = lambda: Decimal("5.00")
    assert recipe.calculate_total_cost() == 1.50


def test_stock_transaction_edge_cases() -> None:
    import pytest

    from app.stock.domain.enums import TransactionType
    from app.stock.domain.transaction import StockTransaction

    # 1. repr
    tx = StockTransaction(
        id=1,
        quantity=MeasuredQuantity(Decimal("10"), "un"),
        type=TransactionType.OUTPUT,
        reason="Ajuste",
    )
    assert "StockTransaction" in repr(tx)

    # 2. ValueError when cost_amount <= 0 for INPUT
    with pytest.raises(ValueError, match="Preço de custo unitário deve ser maior que zero"):
        StockTransaction(
            id=2,
            quantity=MeasuredQuantity(Decimal("10"), "un"),
            type=TransactionType.INPUT,
            cost_amount=Decimal("0.0"),
        )
