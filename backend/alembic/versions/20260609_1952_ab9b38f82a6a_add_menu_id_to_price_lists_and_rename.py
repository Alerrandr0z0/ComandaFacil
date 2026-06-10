"""add_menu_id_to_price_lists_and_rename

Revision ID: ab9b38f82a6a
Revises: 487987cd49f8
Create Date: 2026-06-09 19:52:05.206293+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ab9b38f82a6a'
down_revision: Union[str, None] = '487987cd49f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add menu_id as nullable first, then backfill, then make NOT NULL
    op.add_column('price_lists', sa.Column('menu_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE price_lists
        SET menu_id = menus.id
        FROM menus
        WHERE menus.price_list_id = price_lists.id
        """
    )
    op.alter_column('price_lists', 'menu_id', nullable=False)
    op.create_foreign_key(None, 'price_lists', 'menus', ['menu_id'], ['id'], ondelete='CASCADE')

    # 2) Rename menus.price_list_id -> active_price_list_id, drop FK
    op.drop_constraint(op.f('menus_price_list_id_fkey'), 'menus', type_='foreignkey')
    op.alter_column('menus', 'price_list_id', new_column_name='active_price_list_id')


def downgrade() -> None:
    # 1) Restore FK + column on menus
    op.alter_column('menus', 'active_price_list_id', new_column_name='price_list_id')
    op.create_foreign_key(
        op.f('menus_price_list_id_fkey'), 'menus', 'price_lists',
        ['price_list_id'], ['id'], ondelete='SET NULL',
    )

    # 2) Drop FK + column on price_lists
    op.drop_constraint(None, 'price_lists', type_='foreignkey')
    op.drop_column('price_lists', 'menu_id')
