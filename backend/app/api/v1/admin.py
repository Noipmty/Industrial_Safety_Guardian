"""管理端接口（P8）：文档生命周期 + 知识检索 + chunk 预览 + 审计。

所有接口均要求 admin 角色（``require_admin`` 依赖项）。
每次变更操作都会通过 ``audit_log`` 写入一条审计日志。
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, File, Form, Header, Query, UploadFile, status  # noqa: B008
from sqlalchemy import func, select

from app.core.deps import AdminUser, DbSession
from app.core.exceptions import NotFoundError, ValidationError
from app.core.logger import get_logger
from app.core.redis import get_redis
from app.models.document import DocStatus, DocType, KnowledgeDocument
from app.models.exam import Exam, ExamStatus, Question
from app.models.user import User
from app.schemas.auth import AdminUserResponse
from app.services.audit.logger import (
    ACTION_ADMIN_STATS_VIEW,
    ACTION_DOCUMENT_CHUNK_PREVIEW,
    ACTION_DOCUMENT_DELETE,
    ACTION_DOCUMENT_SEARCH,
    ACTION_DOCUMENT_UPLOAD,
    ACTION_USER_CREATE,
    ACTION_USER_DELETE,
    audit_log,
)
from app.services.indexing.document_parser import parse_document
from app.services.indexing.embedding import get_embedding_service
from app.services.indexing.milvus_store import (
    ensure_collection,
    hybrid_search,
)
from app.services.indexing.plaintext_chunker import recursive_chunk
from app.services.indexing.unified_sync import UnifiedSync

logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["管理"])

UPLOAD_DIR = os.environ.get(
    "GONGAN_UPLOAD_DIR",
    os.path.join(os.getcwd(), "uploads"),
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# 基于 Redis 的进度跟踪（多实例安全）。
# Key: ``upload:progress:{doc_id}``  Value: JSON dict  TTL: 1h
PROGRESS_TTL = 3600


async def _set_progress(doc_id: int, data: dict[str, Any]) -> None:
    """将上传进度存入 Redis（JSON 序列化，TTL 1 小时）。"""
    redis = get_redis()
    await redis.set(f"upload:progress:{doc_id}", json.dumps(data), ex=PROGRESS_TTL)


async def _get_progress(doc_id: int) -> dict[str, Any] | None:
    """从 Redis 读取上传进度；不存在时返回 None。"""
    redis = get_redis()
    raw = await redis.get(f"upload:progress:{doc_id}")
    if raw is None:
        return None
    return json.loads(raw)


async def _del_progress(doc_id: int) -> None:
    """在完成 / 删除后移除进度 key。"""
    redis = get_redis()
    await redis.delete(f"upload:progress:{doc_id}")


def _ip_from_headers(
    x_forwarded_for: str | None = Header(default=None),
) -> str | None:
    """尽力从 X-Forwarded-For 解析客户端 IP（取链路第一个）。"""
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return None


async def _emit_audit(
    db: DbSession,
    user: dict[str, Any],
    action: str,
    x_forwarded_for: str | None = None,
    **extra: Any,
) -> None:
    """单行审计发射器 — 查询用户名后触发写入。"""
    username = f"user_{user['user_id']}"
    try:
        u = await db.get(User, user["user_id"])
        if u is not None:
            username = u.username
    except Exception:  # noqa: BLE001
        logger.debug("Username lookup failed for audit (user_id=%d)", user["user_id"])
    await audit_log(
        user_id=user["user_id"],
        username=username,
        action=action,
        ip_address=_ip_from_headers(x_forwarded_for),
        **extra,
    )


# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------


@router.get("/stats")
async def get_stats(
    db: DbSession,
    user: AdminUser,
    x_forwarded_for: str | None = Header(default=None),
) -> dict[str, Any]:
    """返回仪表盘聚合统计。"""
    await _emit_audit(db, user, ACTION_ADMIN_STATS_VIEW, x_forwarded_for)
    users_count = (
        (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    )
    docs_count = (
        (await db.execute(select(func.count()).select_from(KnowledgeDocument)))
        .scalar()
        or 0
    )
    exams_count = (
        (await db.execute(select(func.count()).select_from(Exam))).scalar() or 0
    )
    questions_count = (
        (await db.execute(select(func.count()).select_from(Question))).scalar()
        or 0
    )

    avg_row = (
        await db.execute(
            select(func.avg(Exam.total_score)).where(
                Exam.status == ExamStatus.GRADED
            )
        )
    ).scalar()
    avg_score = float(avg_row) if avg_row is not None else 0.0

    return {
        "total_users": int(users_count),
        "total_docs": int(docs_count),
        "total_exams": int(exams_count),
        "total_questions": int(questions_count),
        "avg_score": round(avg_score, 2),
    }


# ---------------------------------------------------------------------------
# 文档生命周期
# ---------------------------------------------------------------------------


@router.post("/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),  # noqa: B008
    doc_type: str = Form(...),
    title: str = Form(...),
    version: str = Form("v1"),
    x_forwarded_for: str | None = Header(default=None),
    db: DbSession = None,  # type: ignore[assignment]
    user: AdminUser = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """上传 → 解析 → 分块 → 向量化 → 同步到 Milvus。

    立即返回 ``doc_id``；索引在后台推进。
    可通过 ``GET /admin/documents/{id}/status`` 轮询进度。
    """
    try:
        d_type = DocType(doc_type)
    except ValueError as exc:
        raise ValidationError(f"Invalid doc_type: {doc_type}") from exc

    # 保存上传的文件。
    ext = os.path.splitext(file.filename or "doc.txt")[1].lower()
    fname = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(UPLOAD_DIR, fname)
    content = await file.read()
    with open(path, "wb") as fh:
        fh.write(content)

    # 尽早校验格式。
    try:
        parse_document(path)  # 仅为暴露不支持的格式
    except ValueError as exc:
        os.remove(path)
        raise ValidationError(str(exc)) from exc

    doc = KnowledgeDocument(
        title=title,
        doc_type=d_type,
        source_path=path,
        version=version,
        status=DocStatus.DRAFT,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)

    await _emit_audit(
        db,
        user,
        ACTION_DOCUMENT_UPLOAD,
        x_forwarded_for,
        resource_type="document",
        resource_id=str(doc.id),
        detail={
            "title": title,
            "doc_type": doc_type,
            "version": version,
            "filename": file.filename,
            "size": len(content),
        },
    )

    progress_key = str(doc.id)
    await _set_progress(
        doc.id,
        {
            "status": "processing",
            "progress": 0.0,
            "chunks_count": 0,
            "error": None,
        },
    )

    _run_indexing_task(path, doc_type, version, doc.id, progress_key)
    return {"doc_id": doc.id, "status": "processing"}


def _run_indexing_task(
    path: str,
    doc_type: str,
    version: str,
    doc_id: int,
    progress_key: str,
) -> None:
    """后台任务：解析 → 分块 → 同步到 Milvus。

    内部使用异步循环，在每个阶段更新 Redis 中的进度。
    """

    async def _run() -> None:
        await _set_progress(
            doc_id,
            {"status": "processing", "progress": 10.0, "chunks_count": 0, "error": None},
        )
        parsed = parse_document(path)
        logger.info(
            "Parsed %s: format=%s chars=%d", path, parsed.format, parsed.char_count
        )
        await _set_progress(
            doc_id,
            {"status": "processing", "progress": 25.0, "chunks_count": 0, "error": None},
        )

        chunks = recursive_chunk(parsed.text, chunk_size=500, overlap=50)
        await _set_progress(
            doc_id,
            {"status": "processing", "progress": 50.0, "chunks_count": len(chunks), "error": None},
        )

        sync = UnifiedSync()
        report = await sync.sync_document(
            doc_id=doc_id,
            doc_type=doc_type,
            position="upload",
            version=version,
            chunks=chunks,
        )
        await _set_progress(
            doc_id,
            {"status": "processing", "progress": 95.0, "chunks_count": len(chunks), "error": None},
        )

        from sqlalchemy import update

        from app.core.deps import get_session_factory

        factory = get_session_factory()
        async with factory() as session:
            await session.execute(
                update(KnowledgeDocument)
                .where(KnowledgeDocument.id == doc_id)
                .values(status=DocStatus.PUBLISHED)
            )
            await session.commit()

        await _set_progress(
            doc_id,
            {"status": "done", "progress": 100.0, "chunks_count": len(chunks), "error": None},
        )
        logger.info(
            "Document %d indexed: %d chunks (%d inserted, %d deleted)",
            doc_id,
            report.total_chunks,
            report.inserted,
            report.deleted,
        )

    try:
        asyncio.run(_run())
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document indexing failed")
        asyncio.run(
            _set_progress(
                doc_id,
                {"status": "error", "progress": 0.0, "chunks_count": 0, "error": str(exc)},
            )
        )


def _doc_to_dict(d: KnowledgeDocument) -> dict[str, Any]:
    """序列化文档行。"""
    return {
        "id": d.id,
        "title": d.title,
        "doc_type": (
            d.doc_type.value if hasattr(d.doc_type, "value") else str(d.doc_type)
        ),
        "version": d.version,
        "status": (
            d.status.value if hasattr(d.status, "value") else str(d.status)
        ),
        "created_at": d.created_at,
    }


def _user_to_dict(u: User) -> dict[str, Any]:
    """序列化用户行。"""
    return {
        "id": u.id,
        "username": u.username,
        "real_name": u.real_name,
        "position": (
            u.position.value if hasattr(u.position, "value") else str(u.position)
        ),
        "role": u.role.value if hasattr(u.role, "value") else str(u.role),
        "created_at": u.created_at,
    }


@router.get("/documents")
async def list_documents(
    user: AdminUser = None,  # type: ignore[assignment]
    db: DbSession = None,  # type: ignore[assignment]
) -> list[dict[str, Any]]:
    """列出全部知识文档（最新在前）。"""
    stmt = (
        select(KnowledgeDocument)
        .order_by(KnowledgeDocument.created_at.desc())
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_doc_to_dict(d) for d in rows]


@router.get("/documents/{doc_id}")
async def get_document_detail(
    doc_id: int,
    user: AdminUser = None,  # type: ignore[assignment]
    db: DbSession = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """返回单个文档的元数据。"""
    doc = await db.get(KnowledgeDocument, doc_id)
    if doc is None:
        raise NotFoundError(f"Document {doc_id} not found")
    return _doc_to_dict(doc)


@router.get("/documents/{doc_id}/status")
async def get_document_status(
    doc_id: int,
    user: AdminUser = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """返回文档的处理进度。"""
    progress = await _get_progress(doc_id)
    if progress is None:
        raise NotFoundError(f"Document {doc_id} not found or not processing")
    return progress


@router.get("/documents/{doc_id}/chunks")
async def preview_document_chunks(
    doc_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    x_forwarded_for: str | None = Header(default=None),
    db: DbSession = None,  # type: ignore[assignment]
    user: AdminUser = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """预览文档已索引的 chunks（来自 Milvus）。"""
    await _emit_audit(
        db,
        user,
        ACTION_DOCUMENT_CHUNK_PREVIEW,
        x_forwarded_for,
        resource_type="document",
        resource_id=str(doc_id),
    )
    col = ensure_collection()
    rows = col.query(
        expr=f"doc_id == {doc_id}",
        output_fields=["chunk_id", "chunk_index", "text", "content_hash"],
        limit=limit,
    )
    chunks = sorted(rows, key=lambda r: int(r["chunk_index"]))
    return {
        "doc_id": doc_id,
        "total_chunks": len(rows),
        "chunks": [
            {
                "chunk_id": r["chunk_id"],
                "chunk_index": int(r["chunk_index"]),
                "text": r["text"],
                "content_hash": r["content_hash"],
            }
            for r in chunks
        ],
    }


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    doc_id: int,
    x_forwarded_for: str | None = Header(default=None),
    user: AdminUser = None,  # type: ignore[assignment]
    db: DbSession = None,  # type: ignore[assignment]
) -> None:
    """归档文档并删除其 Milvus chunks。"""
    doc = await db.get(KnowledgeDocument, doc_id)
    if doc is None:
        raise NotFoundError(f"Document {doc_id} not found")
    doc.status = DocStatus.ARCHIVED
    await db.commit()

    await _emit_audit(
        db,
        user,
        ACTION_DOCUMENT_DELETE,
        x_forwarded_for,
        resource_type="document",
        resource_id=str(doc_id),
        detail={"title": doc.title},
    )

    # 尽力清理 Milvus 数据。
    try:
        from app.services.indexing.milvus_store import delete_by_doc

        col = ensure_collection()
        delete_by_doc(col, doc_id)
    except Exception:  # noqa: BLE001
        logger.warning("Best-effort Milvus cleanup failed for doc %d", doc_id)

    await _del_progress(doc_id)


# ---------------------------------------------------------------------------
# 知识检索
# ---------------------------------------------------------------------------


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., min_length=1, max_length=200),
    top_k: int = Query(default=10, ge=1, le=50),
    doc_types: list[str] | None = Query(default=None),  # noqa: B008
    x_forwarded_for: str | None = Header(default=None),
    db: DbSession = None,  # type: ignore[assignment]
    user: AdminUser = None,  # type: ignore[assignment]
) -> dict[str, Any]:
    """知识库混合（dense + sparse）检索。

    使用与 chat RAG 管线相同的 ``hybrid_search`` —
    管理员可直接调用用于 QA / 调试。
    """
    await _emit_audit(
        db,
        user,
        ACTION_DOCUMENT_SEARCH,
        x_forwarded_for,
        detail={"query": q, "top_k": top_k},
    )
    col = ensure_collection()
    embedder = get_embedding_service()
    dense, sparse = embedder.encode([q])
    hits = hybrid_search(
        col,
        dense[0],
        sparse[0],
        top_k=top_k,
        doc_types=doc_types,
    )
    return {"query": q, "total": len(hits), "hits": hits}


# ---------------------------------------------------------------------------
# 用户管理
# ---------------------------------------------------------------------------


@router.get("/users")
async def list_users(
    user: AdminUser = None,  # type: ignore[assignment]
    db: DbSession = None,  # type: ignore[assignment]
) -> list[dict[str, Any]]:
    """列出全部用户。"""
    stmt = select(User).order_by(User.created_at.desc())
    rows = (await db.execute(stmt)).scalars().all()
    return [_user_to_dict(u) for u in rows]


@router.post(
    "/users",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    username: str = Form(...),
    password: str = Form(...),
    real_name: str = Form(...),
    position: str = Form(...),
    role: str = Form("worker"),
    x_forwarded_for: str | None = Header(default=None),
    db: DbSession = None,  # type: ignore[assignment]
    user: AdminUser = None,  # type: ignore[assignment]
) -> AdminUserResponse:
    """创建新用户（仅管理员）。"""
    from app.core.security import pwd_hash

    stmt = select(User).where(User.username == username)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        raise ValidationError(f"Username '{username}' already exists")

    if role not in ("worker", "admin"):
        raise ValidationError("Role must be 'worker' or 'admin'")

    new_user = User(
        username=username,
        password_hash=pwd_hash(password),
        real_name=real_name,
        position=position,
        role=role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await _emit_audit(
        db,
        user,
        ACTION_USER_CREATE,
        x_forwarded_for,
        resource_type="user",
        resource_id=str(new_user.id),
        detail={
            "username": new_user.username,
            "role": new_user.role.value if hasattr(new_user.role, "value") else str(new_user.role),
        },
    )

    return AdminUserResponse(
        id=new_user.id,
        username=new_user.username,
        real_name=new_user.real_name,
        position=(
            new_user.position.value
            if hasattr(new_user.position, "value")
            else str(new_user.position)
        ),
        role=(
            new_user.role.value
            if hasattr(new_user.role, "value")
            else str(new_user.role)
        ),
    )


@router.delete("/users/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    target_id: int,
    x_forwarded_for: str | None = Header(default=None),
    db: DbSession = None,  # type: ignore[assignment]
    user: AdminUser = None,  # type: ignore[assignment]
) -> None:
    """删除用户（不能删除自己）。"""
    if user["user_id"] == target_id:
        raise ValidationError("Cannot delete your own account")
    target = await db.get(User, target_id)
    if target is None:
        raise NotFoundError(f"User {target_id} not found")
    target_username = target.username
    await db.delete(target)
    await db.commit()

    await _emit_audit(
        db,
        user,
        ACTION_USER_DELETE,
        x_forwarded_for,
        resource_type="user",
        resource_id=str(target_id),
        detail={"username": target_username},
    )


# ---------------------------------------------------------------------------
# 审计日志（只读）
# ---------------------------------------------------------------------------


@router.get("/audit-logs")
async def list_audit_logs(
    db: DbSession,
    user: AdminUser,
    action: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """返回分页的审计日志，可带可选过滤条件。

    仅管理员 — 默认返回最近的记录。
    """
    from app.models.audit_log import AuditLog

    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)

    total = (await db.execute(
        select(func.count()).select_from(stmt.subquery())
    )).scalar() or 0

    rows = (
        await db.execute(
            stmt.order_by(AuditLog.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()

    return {
        "total": int(total),
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": r.id,
                "user_id": r.user_id,
                "username": r.username,
                "action": r.action,
                "resource_type": r.resource_type,
                "resource_id": r.resource_id,
                "detail": r.detail,
                "ip_address": r.ip_address,
                "status": r.status,
                "created_at": r.created_at,
            }
            for r in rows
        ],
    }
