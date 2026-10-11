"""FAQ 管理接口 —— 永久缓存层的运营入口（仅管理员）。

链路定位：Redis 语义缓存 miss 后，问答工作流会先匹配 MySQL FAQ
（挖掘沉淀的优质问答），命中则跳过完整 RAG。本模块提供：
- FAQ 的增删改查 / 启停；
- 从近期会话中用 LLM 挖掘 FAQ 候选（管理员审核后采纳入库）。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field
from redis.asyncio import from_url

from app.core.deps import AdminUser
from app.core.logger import get_logger
from app.services.faq import get_faq_service
from app.services.llm.client import get_llm_client
from app.config import get_settings

logger = get_logger(__name__)
router = APIRouter(prefix="/admin/faq", tags=["FAQ管理"])


class FaqUpsertRequest(BaseModel):
    """FAQ 新增 / 更新请求体。"""

    question: str = Field(min_length=2, max_length=512, description="标准问题")
    answer: str = Field(min_length=2, description="精校答案")


class FaqToggleRequest(BaseModel):
    """FAQ 启停请求体。"""

    enabled: bool


@router.get("")
async def list_faq(user: AdminUser) -> list[dict[str, Any]]:
    """全部 FAQ（含停用，供运营查看）。"""
    svc = get_faq_service()
    return await svc.list_all()


@router.post("", status_code=201)
async def create_faq(payload: FaqUpsertRequest, user: AdminUser) -> dict[str, Any]:
    """手动新增 FAQ（自动计算问题向量）。"""
    svc = get_faq_service()
    faq_id = await svc.create(payload.question, payload.answer, source="manual")
    return {"id": faq_id}


@router.put("/{faq_id}")
async def update_faq(
    faq_id: int, payload: FaqUpsertRequest, user: AdminUser
) -> dict[str, str]:
    """更新 FAQ（问题变更时重算向量）。"""
    svc = get_faq_service()
    await svc.update(faq_id, payload.question, payload.answer)
    return {"status": "ok"}


@router.delete("/{faq_id}")
async def delete_faq(faq_id: int, user: AdminUser) -> dict[str, str]:
    """删除 FAQ。"""
    svc = get_faq_service()
    await svc.delete(faq_id)
    return {"status": "ok"}


@router.patch("/{faq_id}/toggle")
async def toggle_faq(
    faq_id: int, payload: FaqToggleRequest, user: AdminUser
) -> dict[str, str]:
    """启用 / 停用 FAQ（停用后不参与匹配）。"""
    svc = get_faq_service()
    await svc.toggle(faq_id, payload.enabled)
    return {"status": "ok"}


@router.post("/mine")
async def mine_faq(user: AdminUser) -> list[dict[str, str]]:
    """从近期会话中挖掘 FAQ 候选（LLM 提炼，返回待审核列表，不入库）。"""
    svc = get_faq_service()
    redis_client = from_url(get_settings().redis.url, decode_responses=True)
    try:
        candidates = await svc.mine_from_sessions(redis_client, get_llm_client())
    finally:
        await redis_client.aclose()
    return candidates
