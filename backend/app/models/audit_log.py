"""审计日志模型 —— 所有管理员变更操作都会持久化到这里。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    """单条审计事件（管理员操作轨迹）。

    由 ``app.services.audit.logger`` 记录 —— 涵盖所有经过认证的管理员变更
    操作以及登录/登出事件，便于合规团队回答"谁在何时何地做了什么"。
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="例如 document.upload / document.delete / user.create / auth.login",
    )
    resource_type: Mapped[str] = mapped_column(
        String(32),
        nullable=True,
        comment="例如 document / user / auth",
    )
    resource_id: Mapped[str] = mapped_column(
        String(128),
        nullable=True,
        comment="目标资源的主键或逻辑标识符",
    )
    detail: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="额外 JSON 载荷（请求体摘录、变更前后对比等）",
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="success",
        comment="success | failure（成功 | 失败）",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        index=True,
        nullable=False,
    )
