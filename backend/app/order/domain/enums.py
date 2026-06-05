from enum import StrEnum


class FulfillmentStatus(StrEnum):
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    RETURNED = "RETURNED"

    def __repr__(self) -> str:
        return f"FulfillmentStatus.{self.name}"


class OrderItemStatus(StrEnum):
    WAITING = "WAITING"
    PREPARING = "PREPARING"
    READY = "READY"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELED"

    def __repr__(self) -> str:
        return f"OrderItemStatus.{self.name}"
