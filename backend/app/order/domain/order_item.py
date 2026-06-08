from app.order.domain.enums import OrderItemStatus
from app.shared.money import Money


class OrderFormItem:
    def __init__(
        self,
        id: int,
        menu_item_id: int,
        name_cpy: str,
        price_cpy: Money,
        station_type_cpy: str,
        quantity: int,
        notes: str = "",
        status: OrderItemStatus = OrderItemStatus.WAITING,
    ) -> None:
        self.id: int = id
        self.menu_item_id: int = menu_item_id
        self.name_cpy: str = name_cpy
        self.price_cpy: Money = price_cpy
        self.station_type_cpy: str = station_type_cpy
        self.status: OrderItemStatus = status

        if quantity <= 0:
            raise ValueError(f"Quantity must be greater than zero, got: {quantity}")
        self.quantity: int = quantity
        self.notes: str = notes

    def calculate_subtotal(self) -> Money:
        return self.price_cpy * self.quantity

    def __repr__(self) -> str:
        return (
            f"OrderFormItem(id={self.id}, name_cpy={self.name_cpy!r}, "
            f"price_cpy={self.price_cpy}, quantity={self.quantity}, status={self.status.value})"
        )
