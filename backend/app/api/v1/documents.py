"""文档查询接口 —— 面向登录用户的知识库文档浏览（权限过滤）。

与 /admin/documents 的区别：
- 仅返回已发布（published）文档；
- 按角色权限过滤文档类型（worker 仅可见公开类型）；
- 不暴露草稿 / 处理中 / 已归档文档。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.core.doc_access import access_level_of, allowed_doc_types
from app.core.exceptions import NotFoundError, PermissionError_
from app.models.document import KnowledgeDocument as Document
from app.services.indexing.milvus_store import ensure_collection

router = APIRouter(prefix="/documents", tags=["文档查询"])


def _doc_view(doc: Document) -> dict[str, Any]:
    return {
        "id": doc.id,
        "title": doc.title,
        "doc_type": doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type),
        "version": doc.version,
        "created_at": doc.created_at,
        "access_level": access_level_of(
            doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
        ),
    }


@router.get("")
async def list_documents(
    user: CurrentUser,
    db: DbSession,
    q: str | None = Query(default=None, max_length=100, description="标题关键词"),
    doc_type: str | None = Query(default=None, max_length=32, description="按类型过滤"),
) -> list[dict[str, Any]]:
    """查询已发布的知识库文档（按角色权限过滤）。"""
    allowed = allowed_doc_types(user["role"])
    if allowed is not None and doc_type and doc_type not in allowed:
        return []
    stmt = select(Document).where(Document.status == "published").order_by(
        Document.created_at.desc()
    )
    if q:
        stmt = stmt.where(Document.title.contains(q))
    if doc_type:
        stmt = stmt.where(Document.doc_type == doc_type)
    rows = (await db.execute(stmt)).scalars().all()
    if allowed is not None:
        rows = [r for r in rows if (r.doc_type.value if hasattr(r.doc_type, "value") else str(r.doc_type)) in allowed]
    return [_doc_view(r) for r in rows]


@router.get("/types")
async def list_doc_types(user: CurrentUser) -> list[dict[str, str]]:
    """当前角色可选的文档类型（用于筛选下拉）。"""
    allowed = allowed_doc_types(user["role"])
    types = [
        {"value": "操作规程", "access_level": access_level_of("操作规程")},
        {"value": "应急处置", "access_level": access_level_of("应急处置")},
        {"value": "事故案例", "access_level": access_level_of("事故案例")},
        {"value": "法规", "access_level": access_level_of("法规")},
        {"value": "风险管控", "access_level": access_level_of("风险管控")},
    ]
    if allowed is None:
        return types
    return [t for t in types if t["value"] in allowed]


@router.get("/{doc_id}")
async def get_document(
    doc_id: int,
    user: CurrentUser,
    db: DbSession,
) -> dict[str, Any]:
    """文档详情 + 已索引的正文片段（仅 published 且有权限）。"""
    doc = (
        await db.execute(select(Document).where(Document.id == doc_id))
    ).scalar_one_or_none()
    if doc is None:
        raise NotFoundError("Document not found")
    doc_type_value = (
        doc.doc_type.value if hasattr(doc.doc_type, "value") else str(doc.doc_type)
    )
    allowed = allowed_doc_types(user["role"])
    if allowed is not None and doc_type_value not in allowed:
        raise PermissionError_("No access to this document type")
    if doc.status != "published":
        raise PermissionError_("Document is not published")

    chunks: list[dict[str, Any]] = []
    try:
        col = ensure_collection()
        rows = col.query(
            expr=f"doc_id == {doc_id}",
            output_fields=["chunk_id", "chunk_index", "text"],
            limit=200,
        )
        chunks = [
            {
                "chunk_index": int(r["chunk_index"]),
                "text": r["text"],
            }
            for r in sorted(rows, key=lambda x: int(x["chunk_index"]))
        ]
    except Exception:  # noqa: BLE001 —— 未索引的文档正文为空
        chunks = []

    view = _doc_view(doc)
    view["chunks"] = chunks
    return view
