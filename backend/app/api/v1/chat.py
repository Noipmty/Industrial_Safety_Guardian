"""对话接口：SSE / JSON 问答 + 会话管理（openapi 契约）。"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import cast

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core import langfuse as lf
from app.core.deps import CurrentUser
from app.core.doc_access import allowed_doc_types, cache_scope
from app.core.exceptions import NotFoundError, PermissionError_
from app.core.logger import get_logger, get_trace_id
from app.schemas.chat import ChatRequest, ChatResponse, ChatSession
from app.workflows.safety_qa.service import get_qa_service

logger = get_logger(__name__)
router = APIRouter(prefix="/chat", tags=["对话"])

SESSION_INDEX = "chat:sessions:{user_id}"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def _touch_session_index(user_id: int, session_id: str, last_message: str) -> None:
    """把会话 upsert 进用户 ZSET，并将元信息写入 context hash。"""
    svc = get_qa_service()
    redis = svc.working_memory.redis
    now = time.time()
    key = SESSION_INDEX.format(user_id=user_id)
    async with redis.pipeline(transaction=True) as pipe:
        pipe.zadd(key, {session_id: now})
        pipe.expire(key, 86400 * 30)
        pipe.hset(
            f"wm:context:{session_id}",
            mapping={
                "user_id": str(user_id),
                "last_message": json.dumps(last_message, ensure_ascii=False),
                "created_at": (
                    await redis.hget(f"wm:context:{session_id}", "created_at")
                    or _utcnow().isoformat()
                ),
                "updated_at": _utcnow().isoformat(),
            },
        )
        await pipe.execute()


@router.post("", response_model=None)
async def chat(payload: ChatRequest, user: CurrentUser):
    """回答安全问题 — JSON 或 SSE 流（契约锁定）。

    权限分离：
    - 普通问答按角色过滤知识库文档类型（worker 仅公开类型）。
    - ``scope="admin"``（仅管理员）为全库检索视图，供管理端问答使用。
    """
    if user["user_id"] != payload.user_id:
        raise PermissionError_("Cannot chat as another user")
    scope_admin = payload.scope == "admin"
    if scope_admin and user["role"] != "admin":
        raise PermissionError_("Admin scope requires admin role")
    svc = get_qa_service()
    session_id = payload.session_id or uuid.uuid4().hex
    trace_id = get_trace_id()
    initial = {
        "session_id": session_id,
        "user_id": payload.user_id,
        "user_position": "",
        "raw_query": payload.message,
        "messages": [],
        "allowed_doc_types": None if scope_admin else allowed_doc_types(user["role"]),
        "cache_scope": cache_scope(user["role"]),
    }

    if not payload.stream:
        with lf.lf_trace(
            "safety-qa",
            user_id=str(payload.user_id),
            session_id=session_id,
            metadata={"query": payload.message},
        ):
            result = await svc.graph.ainvoke(initial)
        await _touch_session_index(
            payload.user_id, session_id, result["generated_response"][:80]
        )
        return ChatResponse(
            response=result["generated_response"],
            intent=result.get("query_type", "factual"),
            sources=result.get("sources", []),
            session_id=session_id,
            trace_id=trace_id,
        )

    return StreamingResponse(
        _sse_stream(svc, initial, payload.user_id, session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _sse_stream(svc, initial: dict, user_id: int, session_id: str):
    """运行 graph，然后按 token → sources → done 顺序发送 SSE 事件。"""
    try:
        with lf.lf_trace(
            "safety-qa",
            user_id=str(user_id),
            session_id=session_id,
            metadata={"query": initial["raw_query"]},
        ):
            result = await svc.graph.ainvoke(initial)
        await _touch_session_index(
            user_id, session_id, result["generated_response"][:80]
        )
        answer = result["generated_response"]
        step = 6
        for i in range(0, len(answer), step):
            yield _sse({"type": "token", "content": answer[i : i + step]})
            await asyncio.sleep(0.01)
        yield _sse(
            {
                "type": "sources",
                "content": json.dumps(
                    result.get("sources", []), ensure_ascii=False
                ),
            }
        )
        yield _sse({"type": "done", "content": ""})
        yield "data: [DONE]\n\n"
    except Exception:  # noqa: BLE001 — 流必须干净地终止
        logger.exception("SSE stream failed")
        yield _sse({"type": "token", "content": "\n\n[服务异常，请稍后重试]"})
        yield _sse({"type": "done", "content": ""})


@router.get("/sessions")
async def list_sessions(
    user: CurrentUser,
    user_id: int = Query(...),
) -> list[ChatSession]:
    """列出用户的会话，最近在前。"""
    if user["user_id"] != user_id:
        raise PermissionError_("Cannot list another user's sessions")
    svc = get_qa_service()
    redis = svc.working_memory.redis
    entries = cast(
        "list[tuple[str, float]]",
        await redis.zrevrange(
            SESSION_INDEX.format(user_id=user_id), 0, 49, withscores=True
        ),
    )
    sessions: list[ChatSession] = []
    for member, score in entries:
        meta = await svc.working_memory.get_context(str(member))
        updated = datetime.fromtimestamp(float(score), tz=timezone.utc)
        created_raw = meta.get("created_at")
        try:
            created = (
                datetime.fromisoformat(created_raw)
                if isinstance(created_raw, str)
                else updated
            )
        except ValueError:
            created = updated
        last = meta.get("last_message", "")
        sessions.append(
            ChatSession(
                session_id=str(member),
                last_message=str(last)[:120] if last else "（新会话）",
                created_at=created,
                updated_at=updated,
            )
        )
    return sessions


@router.get("/sessions/{session_id}/messages")
async def get_messages(
    session_id: str, user: CurrentUser = None  # type: ignore[assignment]
) -> list[dict]:
    """返回会话的近期消息。"""
    svc = get_qa_service()
    messages = await svc.working_memory.get_messages(session_id)
    if not messages:
        raise NotFoundError("Session not found or expired")
    return [
        {
            "role": m["role"],
            "content": m["content"],
            "created_at": _utcnow().isoformat(),
        }
        for m in messages
    ]


@router.post("/sessions/{session_id}/finalize")
async def finalize_session(
    session_id: str, user: CurrentUser = None  # type: ignore[assignment]
) -> dict:
    """会话收尾：整段压缩成 1 条终末摘要（保留 7 天）并清空工作窗口。

    前端在新建会话 / 离开聊天页时调用；摘要同时供长期记忆固化接力。
    """
    svc = get_qa_service()
    summary = await svc.working_memory.finalize_session(session_id)
    if summary is None:
        raise NotFoundError("Session not found or expired")
    return {"session_id": session_id, "summary": summary[:200]}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, user: CurrentUser = None  # type: ignore[assignment]
) -> dict:
    """删除会话：工作记忆 + 索引条目。"""
    svc = get_qa_service()
    user_id = user["user_id"]
    await svc.working_memory.clear_session(session_id)
    await svc.working_memory.redis.zrem(
        SESSION_INDEX.format(user_id=user_id), session_id
    )
    return {"deleted": session_id}
