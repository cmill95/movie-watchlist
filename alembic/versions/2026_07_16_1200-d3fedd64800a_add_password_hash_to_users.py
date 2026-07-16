"""add password_hash to users

Revision ID: d3fedd64800a
Revises: c43eb0f6fac7
Create Date: 2026-07-16 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3fedd64800a"
down_revision: str | Sequence[str] | None = "c43eb0f6fac7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("users", sa.Column("password_hash", sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "password_hash")
