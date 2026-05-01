"""add message parts column

Revision ID: 5f0a3d1c9b2e
Revises: 33ec06183e1b
Create Date: 2026-05-01 14:37:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5f0a3d1c9b2e"
down_revision: str | Sequence[str] | None = "33ec06183e1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("messages", sa.Column("parts", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("messages", "parts")
