"""文档权限模型 —— 知识库内容按文档类型分级，检索结果按角色过滤。

等级定义：
- public     全员可见（安全培训 / 操作规程 / 应急预案）
- internal   主管与管理员可见（国家标准 / 行业规范）

规则：
- worker     仅 public
- supervisor public + internal
- admin      全部（allowed_doc_types 为 None 表示不做检索层过滤）

语义缓存按视图桶隔离（``cache_scope``），避免管理端缓存的全量答案
泄露给受限角色。
"""

from __future__ import annotations

from app.core.logger import get_logger

logger = get_logger(__name__)

# 文档类型 -> 可见等级（与 DocType 枚举值一致）
DOC_ACCESS_LEVELS: dict[str, str] = {
    "操作规程": "public",
    "应急处置": "public",
    "事故案例": "public",
    "法规": "internal",
    "风险管控": "internal",
}

# 角色 -> 可访问的最高等级（含更低等级）
ROLE_MAX_ACCESS: dict[str, str] = {
    "worker": "public",
    "supervisor": "internal",
    "admin": "internal",
}

DEFAULT_DOC_TYPE = "操作规程"


def access_level_of(doc_type: str) -> str:
    """返回文档类型的权限等级，未知类型按 public 处理。"""
    return DOC_ACCESS_LEVELS.get(doc_type, "public")


def allowed_doc_types(role: str) -> list[str] | None:
    """按角色返回允许检索的文档类型列表；admin 返回 None 表示全库不限。"""
    max_level = ROLE_MAX_ACCESS.get(role, "public")
    if role == "admin":
        return None
    return [dt for dt, lv in DOC_ACCESS_LEVELS.items() if _level_rank(lv) <= _level_rank(max_level)]


def can_access(role: str, doc_type: str) -> bool:
    """单个角色 + 文档类型的可见性判断。"""
    if role == "admin":
        return True
    max_level = ROLE_MAX_ACCESS.get(role, "public")
    return _level_rank(access_level_of(doc_type)) <= _level_rank(max_level)


def cache_scope(role: str) -> str:
    """语义缓存视图桶：不同权限级别的答案互相隔离。"""
    return "full" if role == "admin" else ROLE_MAX_ACCESS.get(role, "public")


def _level_rank(level: str) -> int:
    return {"public": 0, "internal": 1, "restricted": 2}.get(level, 0)
