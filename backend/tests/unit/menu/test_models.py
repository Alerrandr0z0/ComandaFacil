from __future__ import annotations

from decimal import Decimal

import pytest

from app.menu.domain.category import Category
from app.menu.domain.menu import Menu, MenuItem
from app.shared.money import Money


def test_category_creation() -> None:
    cat = Category("Bebidas")
    assert cat.name == "Bebidas"
    assert str(cat) == "Bebidas"


def test_category_empty_name() -> None:
    # Empty string is allowed for flat/uncategorized layouts
    cat = Category("")
    assert cat.name == ""
    # Whitespace-only string should still raise ValueError
    with pytest.raises(ValueError, match="Nome da categoria não pode ser vazio"):
        Category("   ")


def test_menu_item_creation() -> None:
    item = MenuItem(
        id=1,
        tenant_id="test",
        name="Feijoada",
        description="Feijoada completa",
        base_price=Money(Decimal("45.00")),
        station_type="GRILL",
        category_name="Pratos",
        image_url="http://img.com/feijoada.jpg",
        is_available=True,
    )
    assert item.id == 1
    assert item.tenant_id == "test"
    assert item.name == "Feijoada"
    assert item.description == "Feijoada completa"
    assert item.base_price == Money(Decimal("45.00"))
    assert item.station_type == "GRILL"
    assert item.category_name == "Pratos"
    assert item.image_url == "http://img.com/feijoada.jpg"
    assert item.is_available is True


def test_menu_item_update_availability() -> None:
    item = MenuItem(
        id=1,
        tenant_id="test",
        name="Suco",
        description="Suco natural",
        base_price=Money(Decimal("10.00")),
        station_type="BEVERAGE",
        category_name="Bebidas",
    )
    assert item.is_available is True
    item.update_availability(False)
    assert item.is_available is False


def test_menu_creation() -> None:
    menu = Menu(
        id=1, tenant_id="test", name="Almoço", description="Cardápio do almoço", is_active=True
    )
    assert menu.id == 1
    assert menu.name == "Almoço"
    assert menu.description == "Cardápio do almoço"
    assert menu.is_active is True
    assert len(menu.categories) == 0


def test_menu_add_item() -> None:
    menu = Menu(id=1, tenant_id="test", name="Jantar")
    menu.add_item_to_category("Pizzas", 101)
    assert len(menu.categories) == 1
    assert menu.categories[0].name == "Pizzas"
    assert len(menu.categories[0].items) == 1
    assert menu.categories[0].items[0].menu_item_id == 101


def test_menu_add_duplicate_item_raises() -> None:
    menu = Menu(id=1, tenant_id="test", name="Jantar")
    menu.add_item_to_category("Pizzas", 101)
    with pytest.raises(ValueError, match="Item com id 101 já existe neste cardápio"):
        menu.add_item_to_category("Pizzas", 101)


def test_menu_remove_item() -> None:
    menu = Menu(id=1, tenant_id="test", name="Jantar")
    menu.add_item_to_category("Pizzas", 101)
    menu.remove_item_from_category("Pizzas", 101)
    # The empty category should be cleaned up automatically
    assert len(menu.categories) == 0


def test_menu_remove_nonexistent_item_raises() -> None:
    menu = Menu(id=1, tenant_id="test", name="Jantar")
    with pytest.raises(ValueError, match="Item com id 99 não encontrado na categoria 'Pizzas'"):
        menu.remove_item_from_category("Pizzas", 99)


def test_menu_activate_deactivate() -> None:
    menu = Menu(id=1, tenant_id="test", name="Almoço", is_active=True)
    assert menu.is_active is True
    menu.deactivate()
    assert menu.is_active is False
    menu.activate()
    assert menu.is_active is True


def test_menu_equality() -> None:
    menu1 = Menu(id=1, tenant_id="test", name="A")
    menu2 = Menu(id=1, tenant_id="test", name="B")
    menu3 = Menu(id=2, tenant_id="test", name="A")
    assert menu1 == menu2
    assert menu1 != menu3
    assert hash(menu1) == hash(menu2)
    assert hash(menu1) != hash(menu3)


def test_menu_item_equality() -> None:
    item1 = MenuItem(
        id=1,
        tenant_id="test",
        name="A",
        description="",
        base_price=Money(Decimal("10")),
        station_type="GRILL",
        category_name="Cat",
    )
    item2 = MenuItem(
        id=1,
        tenant_id="test",
        name="B",
        description="",
        base_price=Money(Decimal("12")),
        station_type="GRILL",
        category_name="Cat",
    )
    item3 = MenuItem(
        id=2,
        tenant_id="test",
        name="A",
        description="",
        base_price=Money(Decimal("10")),
        station_type="GRILL",
        category_name="Cat",
    )
    assert item1 == item2
    assert item1 != item3


def test_menu_representation() -> None:
    menu = Menu(id=1, tenant_id="test", name="Jantar")
    assert "Menu" in repr(menu)
    assert "1" in repr(menu)
    assert "Jantar" in repr(menu)


# ─── PriceList Domain Tests ────────────────────────────────────────────────


def test_price_list_item_creation() -> None:
    from app.menu.domain.price_list import PriceListItem

    money = Money(amount=Decimal("29.90"))
    item = PriceListItem(id=1, price_list_id=10, menu_item_id=5, price=money)
    assert item.id == 1
    assert item.price_list_id == 10
    assert item.menu_item_id == 5
    assert item.price == money


def test_price_list_item_update_price() -> None:
    from app.menu.domain.price_list import PriceListItem

    item = PriceListItem(id=1, price_list_id=10, menu_item_id=5, price=Money(Decimal("10.00")))
    item.update_price(Money(Decimal("15.50")))
    assert item.price.amount == Decimal("15.50")


def test_price_list_creation() -> None:
    import datetime

    from app.menu.domain.price_list import PriceList

    now = datetime.datetime.now(datetime.UTC)
    pl = PriceList(
        id=1,
        tenant_id="test",
        menu_id=1,
        name="Happy Hour",
        description="Preços promocionais",
        valid_from=now,
    )
    assert pl.id == 1
    assert pl.name == "Happy Hour"
    assert pl.is_active is True
    assert len(pl.items) == 0


def test_price_list_add_item() -> None:
    from app.menu.domain.price_list import PriceList, PriceListItem

    pl = PriceList(id=1, tenant_id="test", menu_id=1, name="Regular")
    item = PriceListItem(id=1, price_list_id=1, menu_item_id=10, price=Money(Decimal("25.00")))
    pl.add_item(item)
    assert len(pl.items) == 1


def test_price_list_add_duplicate_item_raises() -> None:
    from app.menu.domain.price_list import PriceList, PriceListItem

    pl = PriceList(id=1, tenant_id="test", menu_id=1, name="Regular")
    item = PriceListItem(id=1, price_list_id=1, menu_item_id=10, price=Money(Decimal("25.00")))
    pl.add_item(item)
    duplicate = PriceListItem(id=2, price_list_id=1, menu_item_id=10, price=Money(Decimal("30.00")))
    with pytest.raises(ValueError, match="Item de menu 10 já possui preço nesta lista"):
        pl.add_item(duplicate)


def test_price_list_remove_item() -> None:
    from app.menu.domain.price_list import PriceList, PriceListItem

    pl = PriceList(id=1, tenant_id="test", menu_id=1, name="Regular")
    pl.add_item(
        PriceListItem(id=1, price_list_id=1, menu_item_id=10, price=Money(Decimal("25.00")))
    )
    pl.remove_item(10)
    assert len(pl.items) == 0


def test_price_list_remove_nonexistent_raises() -> None:
    from app.menu.domain.price_list import PriceList

    pl = PriceList(id=1, tenant_id="test", menu_id=1, name="Regular")
    with pytest.raises(ValueError, match="Item de menu 99 não encontrado nesta lista de preços"):
        pl.remove_item(99)


def test_price_list_get_price() -> None:
    from app.menu.domain.price_list import PriceList, PriceListItem

    pl = PriceList(id=1, tenant_id="test", menu_id=1, name="Regular")
    pl.add_item(
        PriceListItem(id=1, price_list_id=1, menu_item_id=10, price=Money(Decimal("25.00")))
    )
    price = pl.get_price(10)
    assert price is not None
    assert price.amount == Decimal("25.00")

    assert pl.get_price(99) is None


def test_price_list_is_valid_now() -> None:
    import datetime

    from app.menu.domain.price_list import PriceList

    now = datetime.datetime.now(datetime.UTC)
    pl = PriceList(
        id=1,
        tenant_id="test",
        menu_id=1,
        name="Happy Hour",
        valid_from=now - datetime.timedelta(hours=1),
    )
    assert pl.is_valid_now() is True

    future = PriceList(
        id=2,
        tenant_id="test",
        menu_id=1,
        name="Futuro",
        valid_from=now + datetime.timedelta(days=30),
    )
    assert future.is_valid_now() is False

    expired = PriceList(
        id=3,
        tenant_id="test",
        menu_id=1,
        name="Expirado",
        valid_from=now - datetime.timedelta(days=10),
        valid_until=now - datetime.timedelta(days=1),
    )
    assert expired.is_valid_now() is False


def test_price_list_activate_deactivate() -> None:
    from app.menu.domain.price_list import PriceList

    pl = PriceList(id=1, tenant_id="test", menu_id=1, name="Regular", is_active=True)
    assert pl.is_active is True
    pl.deactivate()
    assert pl.is_active is False
    pl.activate()
    assert pl.is_active is True


def test_price_list_equality() -> None:
    from app.menu.domain.price_list import PriceList

    pl1 = PriceList(id=1, tenant_id="test", menu_id=1, name="A")
    pl2 = PriceList(id=1, tenant_id="test", menu_id=1, name="B")
    pl3 = PriceList(id=2, tenant_id="test", menu_id=1, name="A")
    assert pl1 == pl2
    assert pl1 != pl3


def test_money_value_object() -> None:
    m = Money(amount=Decimal("10.50"), currency="BRL")
    assert m.amount == Decimal("10.50")
    assert m.currency == "BRL"
    assert str(m) == "BRL 10.50"


def test_money_addition() -> None:
    a = Money(Decimal("10.00"))
    b = Money(Decimal("5.50"))
    result = a + b
    assert result.amount == Decimal("15.50")


def test_money_multiplication() -> None:
    m = Money(Decimal("10.00"))
    result = m * 3
    assert result.amount == Decimal("30.00")


def test_money_negative_raises() -> None:
    with pytest.raises(ValueError, match="Valor monetário não pode ser negativo"):
        Money(Decimal("-1.00"))


def test_money_zero() -> None:
    z = Money.zero()
    assert z.amount == Decimal("0.00")
    assert z.currency == "BRL"


def test_money_from_float() -> None:
    m = Money.from_float(10.506)
    assert m.amount == Decimal("10.51")
