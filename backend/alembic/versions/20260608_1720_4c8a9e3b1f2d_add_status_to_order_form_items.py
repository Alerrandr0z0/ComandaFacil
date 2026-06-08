"""add_status_to_order_form_items

Revision ID: 4c8a9e3b1f2d
Revises: 9947b94ba12d
Create Date: 2026-06-08 17:20:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c8a9e3b1f2d"
down_revision: str | None = "9947b94ba12d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "order_form_items",
        sa.Column("status", sa.String(length=50), nullable=False, server_default="WAITING"),
    )


def downgrade() -> None:
    op.drop_column("order_form_items", "status")
