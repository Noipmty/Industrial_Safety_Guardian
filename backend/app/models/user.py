"""``users`` 表的用户模型。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.compat import StrEnum
from app.models.base import Base


class Position(StrEnum):
    """钻井队伍岗位。"""

    DRILLER = "司钻"
    ASSISTANT_DRILLER = "副司钻"
    DERRICK_MAN = "井架工"
    ROUGHNECK = "钻工"
    MUD_ENGINEER = "泥浆工"
    SAFETY_OFFICER = "安全管理员"


class Role(StrEnum):
    """系统角色。"""

    WORKER = "worker"
    ADMIN = "admin"


class User(Base):
    """应用用户（钻井队成员或管理员）。"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    username: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    real_name: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    position: Mapped[Position] = mapped_column(
        Enum(Position, name="user_position", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="user_role", values_callable=lambda e: [m.value for m in e]),
        server_default="worker",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
