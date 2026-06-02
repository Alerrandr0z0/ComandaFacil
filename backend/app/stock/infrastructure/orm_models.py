from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_orm import Base


class StockItemORM(Base):
    """SQLAlchemy model for stock_items table."""

    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    current_quantity_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    current_quantity_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    min_stock_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"StockItemORM(id={self.id}, name={self.name!r}, "
            f"qty={self.current_quantity_amount}, unit={self.current_quantity_unit!r})"
        )


class StockMovementORM(Base):
    """SQLAlchemy model for stock_movements table."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_item_id: Mapped[int] = mapped_column(
        ForeignKey("stock_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity_changed: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    reference_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reference_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"StockMovementORM(id={self.id}, item_id={self.stock_item_id}, "
            f"type={self.movement_type!r}, qty={self.quantity_changed})"
        )
