"""SQL 查询工具 —— 结构化业务数据占位实现（P2 范围）。

真实查询（考试统计、用户记录）将随管理端/考试阶段接入；本工具已
实现用户绑定、只读 SELECT 校验，使 planner 可以安全地把它纳入并行
执行。
"""

from __future__ import annotations

import re
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_SELECT_ONLY = re.compile(r"^\s*select\b", re.IGNORECASE)
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|grant|create)\b", re.IGNORECASE
)


class SqlQueryTool:
    """受管控的只读 SQL 工具。以 dict 形式返回行。"""

    def __init__(self, session_factory: Any | None = None) -> None:
        # API 组装阶段接入 MySQL session factory。
        self._session_factory = session_factory

    def validate(self, sql: str) -> None:
        """拒绝一切非普通单条 SELECT 的语句。"""
        if not _SELECT_ONLY.match(sql):
            raise ValueError("Only SELECT statements are allowed")
        if _FORBIDDEN.search(sql):
            raise ValueError("Write keywords detected in SQL")
        if ";" in sql.rstrip(";"):
            raise ValueError("Multiple statements are not allowed")

    async def run(self, sql: str) -> list[dict[str, Any]]:
        """执行校验通过的 SELECT；占位阶段暂返回 []。"""
        self.validate(sql)
        if self._session_factory is None:
            logger.info("SqlQueryTool placeholder: %s", sql[:60])
            return []
        from sqlalchemy import text

        async with self._session_factory() as session:
            result = await session.execute(text(sql))
            return [dict(row._mapping) for row in result.all()]
