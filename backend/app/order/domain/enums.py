from enum import StrEnum


class FulfillmentStatus(StrEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    def __repr__(self) -> str:
        return f"FulfillmentStatus.{self.name}"


class OrderItemStatus(StrEnum):
    WAITING = "WAITING"
    PREPARING = "PREPARING"
    READY = "READY"
    CANCELLED = "CANCELLED"

    def __repr__(self) -> str:
        return f"OrderItemStatus.{self.name}"
