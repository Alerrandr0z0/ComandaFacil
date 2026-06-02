from __future__ import annotations

import datetime
from decimal import Decimal  # noqa: TC003

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_orm import Base


class MenuORM(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    items: Mapped[list[MenuItemORM]] = relationship(
        "MenuItemORM", back_populates="menu", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"MenuORM(id={self.id}, name={self.name!r}, active={self.is_active})"


class MenuItemORM(Base):
    __tablename__ = "menu_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    menu_id: Mapped[int] = mapped_column(ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    menu: Mapped[MenuORM] = relationship("MenuORM", back_populates="items")

    def __repr__(self) -> str:
        return f"MenuItemORM(id={self.id}, name={self.name!r}, category={self.category!r})"


class PriceListORM(Base):
    __tablename__ = "price_lists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    valid_from: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.UTC)
    )
    valid_until: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    items: Mapped[list[PriceListItemORM]] = relationship(
        "PriceListItemORM", back_populates="price_list", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"PriceListORM(id={self.id}, name={self.name!r}, active={self.is_active})"


class PriceListItemORM(Base):
    __tablename__ = "price_list_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_list_id: Mapped[int] = mapped_column(
        ForeignKey("price_lists.id", ondelete="CASCADE"), nullable=False
    )
    menu_item_id: Mapped[int] = mapped_column(
        ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False
    )
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    price_list: Mapped[PriceListORM] = relationship("PriceListORM", back_populates="items")

    def __repr__(self) -> str:
        return (
            f"PriceListItemORM(id={self.id}, menu_item_id={self.menu_item_id}, price={self.price})"
        )
