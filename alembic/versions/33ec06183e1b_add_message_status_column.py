"""add message status column

Revision ID: 33ec06183e1b
Revises: 1d31ea1f542c
Create Date: 2026-05-01 03:58:18.909018

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "33ec06183e1b"
down_revision: str | Sequence[str] | None = "1d31ea1f542c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # 先加 nullable 列（兼容已有数据）
    op.add_column("messages", sa.Column("status", sa.String(length=20), nullable=True, server_default="done"))
    # 填充已有行的默认值
    op.execute("UPDATE messages SET status = 'done' WHERE status IS NULL")
    # 改为 NOT NULL
    op.alter_column("messages", "status", nullable=False)
    # thinking 列（纯新增，nullable）
    op.add_column("messages", sa.Column("thinking", sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("messages", "thinking")
    op.drop_column("messages", "status")
