"""审计日志器 —— 管理员操作的异步持久化。

每次管理员变更以及登录/注册事件都会写入 ``AuditLog`` 行到
MySQL。日志采用 fire-and-forget（发射后不管）模式：失败会被
吞掉并记录 WARNING 日志，审计库的抖动绝不会打断请求。
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.deps import get_session_factory
from app.core.logger import get_logger
from app.models.audit_log import AuditLog

logger = get_logger(__name__)

# 始终写入审计日志的操作。以注册表形式集中维护，
# 便于测试断言覆盖情况，也便于后续 P8 变体（RBAC）
# 检索所有埋点位置。
ACTION_DOCUMENT_UPLOAD = "document.upload"
ACTION_DOCUMENT_DELETE = "document.delete"
ACTION_DOCUMENT_CHUNK_PREVIEW = "document.chunks_preview"
ACTION_DOCUMENT_SEARCH = "document.search"
ACTION_USER_CREATE = "user.create"
ACTION_USER_DELETE = "user.delete"
ACTION_ADMIN_STATS_VIEW = "admin.stats"
ACTION_AUTH_LOGIN = "auth.login"
ACTION_AUTH_REGISTER = "auth.register"


class AuditLogger:
    """围绕异步 DB 会话的轻量封装，用于持久化一条审计记录。

    Usage::

        await audit_logger.log(
            user_id=7,
            username="admin",
            action=ACTION_DOCUMENT_UPLOAD,
            resource_type="document",
            resource_id="42",
            detail={"title": "动火规程"},
            ip_address="127.0.0.1",
            user_agent="curl/8",
        )

    底层的会话工厂通过 ``get_session_factory`` 惰性创建，
    因此导入本模块不会触及 DB 引擎。
    """

    def __init__(self) -> None:
        self._factory: Any = None

    async def log(
        self,
        user_id: int,
        username: str,
        action: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        detail: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        status: str = "success",
    ) -> None:
        """持久化一条审计记录 —— 尽力而为，绝不抛出异常。"""
        try:
            if self._factory is None:
                self._factory = get_session_factory()
            async with self._factory() as session:
                session.add(
                    AuditLog(
                        user_id=user_id,
                        username=username,
                        action=action,
                        resource_type=resource_type,
                        resource_id=resource_id,
                        detail=detail,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        status=status,
                    )
                )
                await session.commit()
        except Exception:  # noqa: BLE001
            logger.exception(
                "Audit log write failed: user=%s action=%s",
                user_id,
                action,
            )


class BackgroundAuditLogger:
    """基于队列的封装，在后台任务中运行 ``AuditLogger.log``。

    适用于无法直接 ``await`` 的同步上下文
    （如 FastAPI 后台任务或同步的 admin 索引任务）。
    """

    def __init__(self) -> None:
        self._inner = AuditLogger()
        self._loop: asyncio.AbstractEventLoop | None = None

    def _get_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop is None:
            try:
                self._loop = asyncio.get_event_loop()
            except RuntimeError:
                # 没有正在运行的事件循环 —— 新建一个（测试、同步上下文）。
                self._loop = asyncio.new_event_loop()
        return self._loop

    def fire(
        self,
        **kwargs: Any,
    ) -> None:
        """调度一次审计日志写入，不阻塞调用方。"""
        loop = self._get_loop()
        try:
            loop.create_task(self._inner.log(**kwargs))
        except RuntimeError:
            # 事件循环已关闭 —— 退化为同步执行。
            asyncio.run(self._inner.log(**kwargs))


# ---------------------------------------------------------------------------
# 单例
# ---------------------------------------------------------------------------

_sync_logger = AuditLogger()
_bg_logger = BackgroundAuditLogger()


async def audit_log(**kwargs: Any) -> None:
    """异步埋点 —— 请求处理器内部优先使用。"""
    await _sync_logger.log(**kwargs)


def audit_log_bg(**kwargs: Any) -> None:
    """同步埋点（fire-and-forget）—— 可在同步上下文中使用。"""
    _bg_logger.fire(**kwargs)
