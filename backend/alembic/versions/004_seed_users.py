"""数据种子迁移：插入一个管理员用户和一个工人用户。

Revision ID: 004
Revises: 003
Create Date: 2026-10-10
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """插入种子用户（密码为 bcrypt 哈希）。"""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "INSERT IGNORE INTO users "
            "(username, password_hash, real_name, position, role) "
            "VALUES "
            "('admin', "
            "'$2b$12$HyGZ2617wQ8OqZ12ZvR1YeZKE6ZQH.yRZ9eQ3ZrhKI/mjdTb9EcC6', "
            "'系统管理员', '安全管理员', 'admin'), "
            "('worker', "
            "'$2b$12$fcij6zZ7y3JhlBmWTnacjemybYt5djS6Vqvs9tIKiNetUhuxSgUQi', "
            "'张三', '司钻', 'worker')"
        )
    )


def downgrade() -> None:
    """删除种子用户。"""
    conn = op.get_bind()
    conn.execute(sa.text("DELETE FROM users WHERE username IN ('admin', 'worker')"))
