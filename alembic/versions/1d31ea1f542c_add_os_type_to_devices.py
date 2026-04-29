"""add os_type to devices

Revision ID: 1d31ea1f542c
Revises: 676e20836e07
Create Date: 2026-04-30 02:24:36.296785

"""

import sqlalchemy as sa

from alembic import op

revision: str = "1d31ea1f542c"
down_revision: str | None = "676e20836e07"
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("devices", sa.Column("os_type", sa.String(length=32), server_default="unknown", nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("devices", "os_type")
