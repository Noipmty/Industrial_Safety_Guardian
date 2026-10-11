"""迁移 005：创建 audit_logs（审计日志）表。

Revision ID: 005
Revises: 004
Create Date: 2026-10-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, index=True),
        sa.Column("username", sa.String(64), nullable=False),
        sa.Column("action", sa.String(64), nullable=False, index=True),
        sa.Column("resource_type", sa.String(32), nullable=True),
        sa.Column("resource_id", sa.String(128), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="success",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.func.current_timestamp(),
            index=True,
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
