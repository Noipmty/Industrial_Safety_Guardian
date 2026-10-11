"""会话整理：将已结束的对话会话压缩进长期记忆。

流程（提示词 §P1）：
    会话结束 -> LLM 生成摘要并抽取事实 -> 双写
    （摘要写入 episodic_memory，每条事实写入 semantic_memory）。
当 LLM 不可用（mock 模式）时，采用确定性的规则抽取，
保证流水线在离线环境下仍可运行。
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.logger import get_logger
from app.services.llm.client import LLMClient, get_llm_client
from app.services.memory.long_term import LongTermMemory

logger = get_logger(__name__)

CONSOLIDATE_PROMPT = """你是安全生产领域的记忆整理助手。请阅读以下对话记录并输出 JSON：
1. summary: 150 字以内的会话摘要（用户关注什么、得到了什么结论）；
2. facts: 用户暴露的长期事实列表，每条为字符串，可能为空；
   - preference: 岗位、职责、偏好（如"用户是电工，关注临时用电规范"）
   - weak_point: 薄弱知识点（如"用户不熟悉动火作业审批流程"）

对话记录：
{transcript}

只输出 JSON 对象：{{"summary": "...", "facts": ["...", ...]}}"""


@dataclass(slots=True)
class ConsolidationResult:
    """单个会话整理的结果。"""

    summary: str
    facts: list[str]
    episodic_id: int | None
    semantic_ids: list[int | None]


def _mock_result(transcript: str) -> tuple[str, list[str]]:
    """规则兜底：简单拼接的摘要 + 近似关键词式的事实条目。"""
    user_lines = [
        line[len("user: "):].strip()
        for line in transcript.splitlines()
        if line.startswith("user: ") and len(line) > 12
    ]
    summary = "用户咨询了：" + "；".join(line[:40] for line in user_lines[:3])
    summary = summary or "（空会话）"
    facts = [
        f"用户提问过：{line[:50]}"
        for line in user_lines[:2]
    ]
    return summary, facts


class SessionConsolidator:
    """将工作记忆中的对话记录压缩进长期记忆。"""

    def __init__(
        self,
        long_term_memory: LongTermMemory,
        llm: LLMClient | None = None,
    ) -> None:
        self._ltm = long_term_memory
        self._llm = llm or get_llm_client()

    async def consolidate_session(
        self,
        user_id: int,
        session_id: str,
        transcript: str,
        importance: float = 0.5,
    ) -> ConsolidationResult:
        """总结单个会话，并双写情景记忆与语义记忆。"""
        summary, facts = await self._extract(transcript)

        episodic_id = await self._ltm.add_episodic(
            user_id=user_id,
            session_id=session_id,
            summary=summary,
            keywords=[fact[:12] for fact in facts[:3]],
            importance=importance,
        )

        semantic_ids: list[int | None] = []
        for fact in facts:
            semantic_ids.append(
                await self._ltm.add_semantic(
                    user_id=user_id,
                    memory_type="preference"
                    if ("用户是" in fact or "岗位" in fact)
                    else "weak_point",
                    content=fact,
                    source_session_id=session_id,
                    importance=importance,
                )
            )

        logger.info(
            "Consolidated session=%s user=%s facts=%s",
            session_id,
            user_id,
            len(facts),
        )
        return ConsolidationResult(
            summary=summary,
            facts=facts,
            episodic_id=episodic_id,
            semantic_ids=semantic_ids,
        )

    async def _extract(self, transcript: str) -> tuple[str, list[str]]:
        """调用 LLM 抽取，失败时降级为规则抽取。"""
        try:
            response = await self._llm.chat(
                messages=[
                    {"role": "system", "content": "你是严格的 JSON 生成器。"},
                    {
                        "role": "user",
                        "content": CONSOLIDATE_PROMPT.format(transcript=transcript[:4000]),
                    },
                ],
                temperature=0.1,
                max_tokens=600,
            )
            parsed = response.json()
            summary = str(parsed.get("summary", "")).strip()
            facts = [str(f).strip() for f in parsed.get("facts", []) if str(f).strip()]
            if not summary:
                raise ValueError("empty summary from LLM")
            return summary, facts[:8]
        except Exception as exc:  # noqa: BLE001 — 降级处理，绝不让主流程崩溃
            logger.warning("LLM consolidation failed, using rule fallback: %s", exc)
            return _mock_result(transcript)


def transcript_from_messages(messages: list[dict]) -> str:
    """将存储的消息列表展平为文本对话记录格式。"""
    return "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)


__all__ = [
    "SessionConsolidator",
    "ConsolidationResult",
    "transcript_from_messages",
    "CONSOLIDATE_PROMPT",
]
