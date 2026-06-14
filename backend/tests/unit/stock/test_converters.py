from decimal import Decimal

import pytest

from app.stock.domain.converters import ImperialConverter


def test_imperial_converter_volume_units() -> None:
    conv = ImperialConverter()
    # Mass conversion (existing)
    assert conv.convert(Decimal("1"), "lb", "oz") == Decimal("16")

    # Volume conversion (missing coverage lines 68-69)
    assert conv.convert(Decimal("2"), "fl_oz", "fl_oz") == Decimal("2")

    # Invalid conversion
    with pytest.raises(ValueError, match="Cannot convert"):
        conv.convert(Decimal("1"), "lb", "fl_oz")
