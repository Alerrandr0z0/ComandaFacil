"""add_display_code_to_order_forms

Revision ID: 1116026255ae
Revises: ab9b38f82a6a
Create Date: 2026-06-09 23:15:56.453626+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1116026255ae"
down_revision: str | None = "ab9b38f82a6a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add display_code column (nullable for existing rows)
    op.add_column(
        "order_forms",
        sa.Column("display_code", sa.String(length=100), nullable=True),
    )

    # Backfill: existing orders get display_code = id::text
    op.execute("UPDATE order_forms SET display_code = id::text WHERE display_code IS NULL")

    # Make NOT NULL after backfill
    op.alter_column("order_forms", "display_code", nullable=False)

    # Partial unique index: only for active (non-paid, non-closed) orders
    op.create_index(
        "uq_active_display_code",
        "order_forms",
        ["tenant_id", "display_code"],
        unique=True,
        postgresql_where=sa.text("state NOT IN ('PAID', 'CLOSED')"),
    )


def downgrade() -> None:
    op.drop_index("uq_active_display_code")
    op.drop_column("order_forms", "display_code")
