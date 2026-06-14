from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_orm import Base


class StockItemORM(Base):
    """SQLAlchemy model for stock_items table."""

    __tablename__ = "stock_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    # SIMPLE or COMPOSITE
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="SIMPLE")
    unit: Mapped[str] = mapped_column(String(20), nullable=False, default="un")
    min_stock_level: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"StockItemORM(id={self.id}, name={self.name!r}, "
            f"type={self.type!r}, unit={self.unit!r})"
        )


class CompositeStockItemRelationORM(Base):
    """SQLAlchemy model mapping parent composite items to children items."""

    __tablename__ = "composite_stock_item_relations"

    parent_id: Mapped[int] = mapped_column(
        ForeignKey("stock_items.id", ondelete="CASCADE"), primary_key=True
    )
    child_id: Mapped[int] = mapped_column(
        ForeignKey("stock_items.id", ondelete="CASCADE"), primary_key=True
    )


class StockTransactionORM(Base):
    """SQLAlchemy model for stock_transactions table."""

    __tablename__ = "stock_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stock_item_id: Mapped[int] = mapped_column(
        ForeignKey("stock_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_type: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    cost_amount: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"StockTransactionORM(id={self.id}, item_id={self.stock_item_id}, "
            f"type={self.transaction_type!r}, qty={self.quantity_value}{self.quantity_unit})"
        )


class RecipeORM(Base):
    """SQLAlchemy model for recipes table."""

    __tablename__ = "recipes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_item_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RecipeIngredientORM(Base):
    """SQLAlchemy model for recipe_ingredients table."""

    __tablename__ = "recipe_ingredients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    recipe_id: Mapped[int] = mapped_column(
        ForeignKey("recipes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stock_item_id: Mapped[int] = mapped_column(
        ForeignKey("stock_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity_value: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    quantity_unit: Mapped[str] = mapped_column(String(20), nullable=False)
