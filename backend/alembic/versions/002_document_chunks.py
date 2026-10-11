"""为 unified_sync 新增 document_chunks 记账表（P1）。

Revision ID: 002
Revises: 001
Create Date: 2026-10-10
"""

import sqlalchemy as sa

from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """创建分块哈希记账表。"""
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
        sa.Column("doc_id", sa.BigInteger, nullable=False, index=True),
        sa.Column("chunk_index", sa.BigInteger, nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.UniqueConstraint("doc_id", "chunk_index", name="uq_doc_chunk_index"),
    )


def downgrade() -> None:
    """删除分块哈希记账表。"""
    op.drop_table("document_chunks")
