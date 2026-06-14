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
        delivered_quantity: int = 0,
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
        if delivered_quantity < 0 or delivered_quantity > quantity:
            raise ValueError(
                f"delivered_quantity must be between 0 and quantity, got: {delivered_quantity}"
            )
        self.delivered_quantity: int = delivered_quantity
        self.notes: str = notes

    def mark_delivered(self, qty: int = 0) -> None:
        if qty <= 0:
            qty = self.quantity - self.delivered_quantity
        self.delivered_quantity += qty
        if self.delivered_quantity >= self.quantity:
            self.status = OrderItemStatus.DELIVERED
        else:
            self.status = OrderItemStatus.PARTIALLY_DELIVERED

    def mark_canceled(self) -> None:
        self.status = OrderItemStatus.CANCELED

    def calculate_subtotal(self) -> Money:
        return self.price_cpy * self.quantity

    def __repr__(self) -> str:
        return (
            f"OrderFormItem(id={self.id}, name_cpy={self.name_cpy!r}, "
            f"price_cpy={self.price_cpy}, quantity={self.quantity}, status={self.status.value})"
        )
