"""工作记忆 —— Redis List + Hash（TTL 2 小时）+ 滚动/终末压缩。

压缩策略（按设计）：
- 会话未过期：保留最近 10 条原文，更早的全部由 LLM 压缩成 1 条摘要消息
  （role="summary"）置于列表头部 —— 长对话的记忆连贯性不随裁剪丢失；
- 会话过期（结束）：整段对话压缩成 1 条终末摘要存 ``wm:digest:{session_id}``
  （保留 7 天），随后清空工作窗口，配合长期记忆固化完成会话收尾。

LLM 不可用时降级：压缩退化为"截断拼接"（保住最近要点，不阻塞写入）。
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from typing import Any

from redis.asyncio import Redis, from_url

from app.config import get_settings

WINDOW_SIZE = 20  # 无摘要器时的旧行为：滚动裁剪到 20 条
KEEP_RECENT = 10  # 滚动压缩后保留的原文条数
COMPRESS_TRIGGER = 12  # 原文超过该条数触发滚动压缩
TTL_SECONDS = 7200  # 2 小时
DIGEST_TTL_SECONDS = 7 * 86400  # 终末摘要保留 7 天

Summarizer = Callable[[list[dict[str, str]]], Awaitable[str]]


def fallback_summary(messages: list[dict[str, str]], max_chars: int = 400) -> str:
    """LLM 不可用时的兜底压缩：按顺序截断拼接要点。"""
    parts: list[str] = []
    total = 0
    for m in messages:
        role = "用户" if m.get("role") == "user" else "助手"
        text = str(m.get("content", "")).replace("\n", " ")[:60]
        piece = f"{role}:{text}"
        if total + len(piece) > max_chars:
            parts.append("……")
            break
        parts.append(piece)
        total += len(piece)
    return "；".join(parts)


class WorkingMemory:
    """基于 Redis 的会话级短期记忆（含两级压缩）。"""

    def __init__(
        self,
        redis: Redis | None = None,
        summarizer: Summarizer | None = None,
    ) -> None:
        self._redis = redis if redis is not None else from_url(
            get_settings().redis.url, decode_responses=True
        )
        self._summarizer = summarizer

    @property
    def redis(self) -> Redis:
        """暴露底层客户端（供测试 / pipeline 使用）。"""
        return self._redis

    @staticmethod
    def _messages_key(session_id: str) -> str:
        return f"wm:messages:{session_id}"

    @staticmethod
    def _context_key(session_id: str) -> str:
        return f"wm:context:{session_id}"

    @staticmethod
    def _digest_key(session_id: str) -> str:
        return f"wm:digest:{session_id}"

    # ------------------------------------------------------------------
    # 写入 + 滚动压缩（未过期会话：10 条原文 + 头部 1 条摘要）
    # ------------------------------------------------------------------
    async def add_message(
        self, session_id: str, role: str, content: str
    ) -> None:
        """追加一条消息并刷新 TTL；原文超阈值时触发滚动压缩。"""
        entry = json.dumps(
            {"role": role, "content": content}, ensure_ascii=False
        )
        key = self._messages_key(session_id)
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.rpush(key, entry)
            pipe.expire(key, TTL_SECONDS)
            await pipe.execute()
        if self._summarizer is not None:
            try:
                llen = await self._redis.llen(key)
            except Exception:  # noqa: BLE001 —— 计数失败按旧行为裁剪
                llen = 0
            if llen > COMPRESS_TRIGGER:
                await self._rollover(session_id, key, llen)
        else:
            await self._redis.ltrim(key, -WINDOW_SIZE, -1)

    async def _rollover(self, session_id: str, key: str, llen: int) -> None:
        """保留最近 10 条原文，把更早的消息压成 1 条摘要置于头部。"""
        old_raw = await self._redis.lrange(key, 0, -(KEEP_RECENT + 1))
        if not old_raw:
            return
        recent_raw = await self._redis.lrange(key, -KEEP_RECENT, -1)
        old_messages = [json.loads(item) for item in old_raw]
        try:
            summary = await self._summarizer(old_messages)  # type: ignore[misc]
        except Exception:  # noqa: BLE001 —— LLM 失败降级为截断拼接
            summary = fallback_summary(old_messages)
        summary_entry = json.dumps(
            {
                "role": "summary",
                "content": summary,
                "covers": len(old_messages),
                "ts": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
        )
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(key)
            pipe.rpush(key, summary_entry)
            for item in recent_raw:
                pipe.rpush(key, item)
            pipe.expire(key, TTL_SECONDS)
            await pipe.execute()

    # ------------------------------------------------------------------
    # 终末压缩（会话过期/结束：整段 → 1 条摘要，保留 7 天）
    # ------------------------------------------------------------------
    async def finalize_session(self, session_id: str) -> str | None:
        """收尾会话：全部消息压成 1 条终末摘要，清空工作窗口。

        返回摘要文本（供调用方接力长期记忆固化）；空会话返回 None。
        """
        key = self._messages_key(session_id)
        raw = await self._redis.lrange(key, 0, -1)
        if not raw:
            return None
        messages = [json.loads(item) for item in raw]
        if self._summarizer is not None:
            try:
                summary = await self._summarizer(messages)  # type: ignore[misc]
            except Exception:  # noqa: BLE001
                summary = fallback_summary(messages)
        else:
            summary = fallback_summary(messages)
        digest = json.dumps(
            {
                "summary": summary,
                "message_count": len(messages),
                "finalized_at": datetime.now(timezone.utc).isoformat(),
            },
            ensure_ascii=False,
        )
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(self._digest_key(session_id), digest, ex=DIGEST_TTL_SECONDS)
            pipe.delete(key, self._context_key(session_id))
            await pipe.execute()
        return summary

    async def get_digest(self, session_id: str) -> dict[str, Any] | None:
        """读取会话终末摘要（不存在返回 None）。"""
        raw = await self._redis.get(self._digest_key(session_id))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # 读取
    # ------------------------------------------------------------------
    async def get_messages(
        self, session_id: str, limit: int = WINDOW_SIZE
    ) -> list[dict[str, Any]]:
        """按最旧在前返回末尾 ``limit`` 条（可能含头部 summary 条目）。"""
        raw = await self._redis.lrange(self._messages_key(session_id), -limit, -1)
        return [json.loads(item) for item in raw]

    async def set_context(self, session_id: str, fields: dict[str, Any]) -> None:
        """将字段合并进会话上下文 Hash 并刷新 TTL。"""
        key = self._context_key(session_id)
        serialized: dict[str, str] = {
            k: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)
            for k, v in fields.items()
        }
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.hset(key, mapping=serialized)  # type: ignore[arg-type]
            pipe.expire(key, TTL_SECONDS)
            await pipe.execute()

    async def get_context(self, session_id: str) -> dict[str, Any]:
        """返回全部上下文字段，尽可能解码 JSON 值。"""
        raw = await self._redis.hgetall(self._context_key(session_id))
        decoded: dict[str, Any] = {}
        for key, value in raw.items():
            str_key = str(key)
            try:
                decoded[str_key] = json.loads(value)
            except (TypeError, ValueError):
                decoded[str_key] = value
        return decoded

    async def get_context_field(self, session_id: str, field: str) -> Any:
        """返回单个上下文字段（已解码），不存在时返回 None。"""
        value = await self._redis.hget(self._context_key(session_id), field)
        if value is None:
            return None
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return value

    async def clear_session(self, session_id: str) -> None:
        """清除某个会话的所有工作记忆 key（含终末摘要）。"""
        await self._redis.delete(
            self._messages_key(session_id),
            self._context_key(session_id),
            self._digest_key(session_id),
        )
