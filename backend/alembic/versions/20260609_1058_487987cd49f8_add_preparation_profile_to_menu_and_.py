"""add_preparation_profile_to_menu_and_kitchen

Revision ID: 487987cd49f8
Revises: c7c2dbc5d5de
Create Date: 2026-06-09 10:58:49.884086+00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '487987cd49f8'
down_revision: str | None = 'c7c2dbc5d5de'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('kitchen_order_items', sa.Column('preparation_profile', sa.String(length=50), nullable=False, server_default='STANDARD'))
    op.add_column('menu_items', sa.Column('preparation_profile', sa.String(length=50), nullable=False, server_default='STANDARD'))


def downgrade() -> None:
    op.drop_column('menu_items', 'preparation_profile')
    op.drop_column('kitchen_order_items', 'preparation_profile')
