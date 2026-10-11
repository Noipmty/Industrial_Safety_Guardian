"""006: 新增 FAQ 永久缓存表。"""

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

from alembic import op  # noqa: E402
import sqlalchemy as sa  # noqa: E402


def upgrade() -> None:
    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("question", sa.String(512), nullable=False, comment="标准问题"),
        sa.Column("answer", sa.Text(), nullable=False, comment="精校答案"),
        sa.Column("embedding", sa.Text(), nullable=False, comment="问题向量 JSON"),
        sa.Column(
            "source", sa.String(16), nullable=False, server_default="manual",
            comment="来源 manual/mined",
        ),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_faqs_enabled", "faqs", ["enabled"])


def downgrade() -> None:
    op.drop_table("faqs")
