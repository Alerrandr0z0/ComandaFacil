"""add_notes_to_kitchen_order_items

Revision ID: 61dd452cea45
Revises: 1116026255ae
Create Date: 2026-06-10 00:28:45.502846+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "61dd452cea45"
down_revision: str | None = "1116026255ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("kitchen_order_items", sa.Column("notes", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("kitchen_order_items", "notes")
