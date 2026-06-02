from __future__ import annotations

from decimal import Decimal  # noqa: TC003

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_orm import Base


class PaymentORM(Base):
    """SQLAlchemy model for payments table."""

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    method: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="PENDING")
    gateway_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    failure_reason: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)

    def __repr__(self) -> str:
        return (
            f"PaymentORM(id={self.id}, order_id={self.order_id}, tenant_id={self.tenant_id!r}, "
            f"amount={self.amount}, method={self.method!r}, status={self.status!r}, "
            f"failure_reason={self.failure_reason!r})"
        )
