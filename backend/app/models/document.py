"""知识文档与会话模型。"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.compat import StrEnum
from app.models.base import Base, TimestampMixin


class DocType(StrEnum):
    """知识文档类别。"""

    REGULATION = "法规"
    OPERATION_PROCEDURE = "操作规程"
    RISK_CONTROL = "风险管控"
    ACCIDENT_CASE = "事故案例"
    EMERGENCY_RESPONSE = "应急处置"


class DocStatus(StrEnum):
    """文档生命周期状态。"""

    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class KnowledgeDocument(Base):
    """录入系统的安全知识文档。"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    title: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    doc_type: Mapped[DocType] = mapped_column(
        Enum(DocType, name="document_doc_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    source_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    version: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    status: Mapped[DocStatus] = mapped_column(
        Enum(DocStatus, name="document_status", values_callable=lambda e: [m.value for m in e]),
        server_default="draft",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )


class Session(Base, TimestampMixin):
    """用户与安全助手之间的一次聊天会话。"""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    session_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    messages: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    user_position: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
