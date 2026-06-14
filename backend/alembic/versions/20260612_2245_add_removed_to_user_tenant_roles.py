"""add_removed_to_user_tenant_roles

Revision ID: b2c3d4e5f6a7
Revises: afa78038d50d
Create Date: 2026-06-12 22:45:00.000000+00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "afa78038d50d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user_tenant_roles",
        sa.Column("removed", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("user_tenant_roles", "removed")
