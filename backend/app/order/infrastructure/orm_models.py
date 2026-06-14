from __future__ import annotations

import datetime
from decimal import Decimal  # noqa: TC003

import sqlalchemy as sa
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_orm import Base


class OrderFormORM(Base):
    """SQLAlchemy model for order_forms table."""

    __tablename__ = "order_forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_code: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    payment_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.datetime.now(datetime.UTC),
        server_default=sa.func.now(),
    )

    # Strategy pattern flattened fields
    fulfillment_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Table strategy fields
    table_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Takeaway strategy fields
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Delivery strategy fields
    delivery_street: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_neighborhood: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    delivery_state: Mapped[str | None] = mapped_column(String(50), nullable=True)
    delivery_postal_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    delivery_estimated_time: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_tracking_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    delivery_state_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    items: Mapped[list[OrderFormItemORM]] = relationship(
        "OrderFormItemORM", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"OrderFormORM(id={self.id}, tenant_id={self.tenant_id!r}, state={self.state!r}, fulfillment_type={self.fulfillment_type!r})"


class OrderFormItemORM(Base):
    """SQLAlchemy model for order_form_items table."""

    __tablename__ = "order_form_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("order_forms.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name_cpy: Mapped[str] = mapped_column(String(255), nullable=False)
    price_cpy: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    station_type_cpy: Mapped[str] = mapped_column(String(100), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    delivered_quantity: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=sa.text("0")
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="WAITING")

    # Relationships
    order: Mapped[OrderFormORM] = relationship("OrderFormORM", back_populates="items")

    def __repr__(self) -> str:
        return f"OrderFormItemORM(id={self.id}, menu_item_id={self.menu_item_id}, name={self.name_cpy!r}, quantity={self.quantity})"
