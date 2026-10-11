"""为 exams 增加 time_limit 字段，并为 exam_answers 添加唯一约束。

Revision ID: 003
Revises: 002
Create Date: 2026-10-10
"""

import sqlalchemy as sa

from alembic import op

# Alembic 使用的版本标识。
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增 time_limit 字段与幂等唯一约束。"""
    op.add_column(
        "exams",
        sa.Column(
            "time_limit",
            sa.BigInteger,
            nullable=False,
            server_default=sa.text("3600"),
        ),
    )
    op.create_unique_constraint(
        "uq_exam_question", "exam_answers", ["exam_id", "question_id"]
    )


def downgrade() -> None:
    """回滚 P5 迁移的变更。"""
    op.drop_constraint("uq_exam_question", "exam_answers", type_="unique")
    op.drop_column("exams", "time_limit")
