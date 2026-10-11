"""工安卫士后端的初始库表迁移。

创建六张业务表：users（用户）、documents（文档）、sessions（会话）、
questions（题目）、exams（考试）、exam_answers（答卷）。

Revision ID: 001
Revises:
Create Date: 2026-10-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects.mysql import TINYINT

from alembic import op

# Alembic 使用的版本标识。
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建全部 P0 业务表。"""

    # -- users（用户表）-------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(256), nullable=False),
        sa.Column("real_name", sa.String(64), nullable=False),
        sa.Column(
            "position",
            sa.Enum(
                "司钻",
                "副司钻",
                "井架工",
                "钻工",
                "泥浆工",
                "安全管理员",
                name="user_position",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum("worker", "admin", name="user_role", create_type=False),
            nullable=False,
            server_default="worker",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # -- documents（文档表）---------------------------------------------------
    op.create_table(
        "documents",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column(
            "doc_type",
            sa.Enum(
                "法规",
                "操作规程",
                "风险管控",
                "事故案例",
                "应急处置",
                name="document_doc_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("source_path", sa.String(512), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "published",
                "archived",
                name="document_status",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # -- sessions（会话表）----------------------------------------------------
    op.create_table(
        "sessions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("session_id", sa.String(64), nullable=False, unique=True),
        sa.Column("messages", sa.JSON, nullable=True),
        sa.Column("user_position", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # -- questions（题目表）---------------------------------------------------
    op.create_table(
        "questions",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "doc_id",
            sa.BigInteger,
            sa.ForeignKey("documents.id"),
            nullable=True,
        ),
        sa.Column(
            "question_type",
            sa.Enum(
                "single",
                "multiple",
                "judge",
                "short_answer",
                name="question_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("stem", sa.Text, nullable=False),
        sa.Column("options", sa.JSON, nullable=True),
        sa.Column("answer", sa.Text, nullable=False),
        sa.Column("explanation", sa.Text, nullable=True),
        sa.Column("knowledge_tags", sa.JSON, nullable=True),
        sa.Column("position_tags", sa.JSON, nullable=True),
        sa.Column(
            "difficulty",
            TINYINT,
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.Column("source_chunk_id", sa.String(128), nullable=True),
        sa.Column(
            "verified",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # -- exams（考试表）-------------------------------------------------------
    op.create_table(
        "exams",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.BigInteger,
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("position", sa.String(32), nullable=False),
        sa.Column("question_ids", sa.JSON, nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "created",
                "submitted",
                "graded",
                name="exam_status_enum",
                create_type=False,
            ),
            nullable=False,
            server_default="created",
        ),
        sa.Column("total_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime,
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("submitted_at", sa.DateTime, nullable=True),
    )

    # -- exam_answers（答卷表）------------------------------------------------
    op.create_table(
        "exam_answers",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column(
            "exam_id",
            sa.BigInteger,
            sa.ForeignKey("exams.id"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.BigInteger,
            sa.ForeignKey("questions.id"),
            nullable=False,
        ),
        sa.Column("user_answer", sa.Text, nullable=True),
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("grading_detail", sa.JSON, nullable=True),
        sa.Column(
            "graded_by",
            sa.Enum(
                "auto",
                "manual",
                name="exam_answer_graded_by",
                create_type=False,
            ),
            nullable=False,
            server_default="auto",
        ),
    )


def downgrade() -> None:
    """按依赖逆序删除全部 P0 业务表。"""

    op.drop_table("exam_answers")
    op.drop_table("exams")
    op.drop_table("questions")
    op.drop_table("sessions")
    op.drop_table("documents")
    op.drop_table("users")
