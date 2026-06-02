"""create_stock_schema

Revision ID: 5e8a2f9b3c1d
Revises: 92630e2a4cc4
Create Date: 2026-06-02 14:30:00.000000+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5e8a2f9b3c1d"
down_revision: str | None = "92630e2a4cc4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stock_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("current_quantity_amount", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("current_quantity_unit", sa.String(length=20), nullable=False),
        sa.Column("min_stock_level", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stock_items_tenant_id"), "stock_items", ["tenant_id"], unique=False
    )
    op.create_index(
        op.f("ix_stock_items_name_tenant"),
        "stock_items",
        ["name", "tenant_id"],
        unique=True,
    )

    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_item_id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("quantity_changed", sa.Float(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stock_item_id"], ["stock_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_stock_movements_stock_item_id"),
        "stock_movements",
        ["stock_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_stock_movements_stock_item_id"), table_name="stock_movements"
    )
    op.drop_table("stock_movements")
    op.drop_index(
        op.f("ix_stock_items_name_tenant"), table_name="stock_items"
    )
    op.drop_index(op.f("ix_stock_items_tenant_id"), table_name="stock_items")
    op.drop_table("stock_items")
