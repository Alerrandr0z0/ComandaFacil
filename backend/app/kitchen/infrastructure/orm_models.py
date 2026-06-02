from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_orm import Base


class KitchenOrderItemORM(Base):
    """SQLAlchemy model for kitchen_order_items table."""

    __tablename__ = "kitchen_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    correlation_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    name_cpy: Mapped[str] = mapped_column(String(255), nullable=False)
    station_type_cpy: Mapped[str] = mapped_column(String(100), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="WAITING")

    def __repr__(self) -> str:
        return (
            f"KitchenOrderItemORM(id={self.id}, correlation_id={self.correlation_id}, "
            f"name={self.name_cpy!r}, station={self.station_type_cpy!r}, state={self.state!r})"
        )


class KitchenStationORM(Base):
    """SQLAlchemy model for kitchen_stations table using Single Table Inheritance."""

    __tablename__ = "kitchen_stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    station_type: Mapped[str] = mapped_column(String(100), nullable=False)

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_on": "station_type",
        "polymorphic_identity": "STATION",
    }

    def __repr__(self) -> str:
        return (
            f"KitchenStationORM(id={self.id}, tenant_id={self.tenant_id!r}, "
            f"is_active={self.is_active}, station_type={self.station_type!r})"
        )


class GrillORM(KitchenStationORM):
    """SQLAlchemy model representing Grill stations."""

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": "GRILL",
    }


class BeverageORM(KitchenStationORM):
    """SQLAlchemy model representing Beverage stations."""

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": "BEVERAGE",
    }
