"""重置种子用户密码为已知明文（admin8888 / worker1234）。

Revision ID: 007
Revises: 006
Create Date: 2026-10-13
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """更新 admin / worker 的密码哈希为已知明文的 bcrypt 哈希。"""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE users SET password_hash = "
            "'$2b$12$/h0uStzmsO.G6ZOE2gEj0eQK9xQvtN1RHJMukwq2AUBbsSeUh7RCW' "
            "WHERE username = 'admin'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE users SET password_hash = "
            "'$2b$12$aXXnz0sS6kHc/kuepI7yYOYm0A3h51UX2N/UT5gfdpJ70ffHXFHN6' "
            "WHERE username = 'worker'"
        )
    )


def downgrade() -> None:
    """恢复原始种子哈希。"""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "UPDATE users SET password_hash = "
            "'$2b$12$HyGZ2617wQ8OqZ12ZvR1YeZKE6ZQH.yRZ9eQ3ZrhKI/mjdTb9EcC6' "
            "WHERE username = 'admin'"
        )
    )
    conn.execute(
        sa.text(
            "UPDATE users SET password_hash = "
            "'$2b$12$fcij6zZ7y3JhlBmWTnacjemybYt5djS6Vqvs9tIKiNetUhuxSgUQi' "
            "WHERE username = 'worker'"
        )
    )
