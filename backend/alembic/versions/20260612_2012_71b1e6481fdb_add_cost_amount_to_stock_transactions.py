"""add_cost_amount_to_stock_transactions

Revision ID: 71b1e6481fdb
Revises: 61dd452cea45
Create Date: 2026-06-12 20:12:27.978544+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "71b1e6481fdb"
down_revision: str | None = "61dd452cea45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add column with a temporary default to avoid constraint errors on existing data
    op.add_column(
        "stock_transactions",
        sa.Column(
            "cost_amount", sa.Numeric(precision=12, scale=4), nullable=False, server_default="0.0"
        ),
    )
    # Remove default so that subsequent inserts must provide it
    op.alter_column("stock_transactions", "cost_amount", server_default=None)


def downgrade() -> None:
    op.drop_column("stock_transactions", "cost_amount")
