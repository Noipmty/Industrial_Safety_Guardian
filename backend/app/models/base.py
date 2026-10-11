"""SQLAlchemy 声明式基类与通用 mixin。"""

from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 模型的声明式基类。"""

    pass


class TimestampMixin:
    """为模型添加 ``created_at`` 和 ``updated_at`` 列的 mixin。

    两个列都在数据库层面默认取当前时间戳。
    ``updated_at`` 通过 ``onupdate`` 在每次 UPDATE 时自动刷新。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
