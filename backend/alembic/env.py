"""工安卫士后端的异步 Alembic 环境。

数据库 URL 从 ``app.config``（``settings.mysql.url``）读取，而不是从
alembic.ini 读取，以确保密钥不会出现在纳入版本控制的配置文件中。
同时支持离线（生成 SQL 脚本）与在线（连接真实数据库）两种迁移方式；
在线迁移使用异步引擎。
"""

import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# 确保 backend/ 目录可导入，以便 `app.*` 能正确解析。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings  # noqa: E402
from app.models import Base  # noqa: E402

# --------------------------------------------------------------------------- #
# Alembic 配置初始化
# --------------------------------------------------------------------------- #

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 注入真实的数据库 URL，覆盖 alembic.ini 中的占位符。
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.mysql.url)


# --------------------------------------------------------------------------- #
# 离线迁移
# --------------------------------------------------------------------------- #


def run_migrations_offline() -> None:
    """无需连接真实数据库，直接生成 SQL 脚本。"""

    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------------------------------- #
# 在线迁移（异步）
# --------------------------------------------------------------------------- #


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """使用异步引擎对真实数据库执行迁移。"""

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


# --------------------------------------------------------------------------- #
# 入口
# --------------------------------------------------------------------------- #

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
