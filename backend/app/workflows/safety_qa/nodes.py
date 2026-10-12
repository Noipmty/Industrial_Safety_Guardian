"""安全问答工作流的 7 个 LangGraph node。

顺序（prompt §P2）：
    understand -> cache_lookup -> retrieve_memory -> plan_tools
    -> execute_tools -> quality_gate -> fuse_respond

每个 node 都是对 :class:`QAContext` 的闭包，使依赖（LLM、工具、
缓存）保持可注入、可测试。所有 node 均为 LLM mock / 离线运行保留
确定性的降级路径。
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core import langfuse as lf
from app.core.doc_access import access_level_of
from app.core.logger import get_logger, get_trace_id
from app.prompts.guard import (
    FUSE_ANSWER_SYSTEM,
    FUSE_ANSWER_USER,
    QUERY_UNDERSTAND_SYSTEM,
    screen_query,
)
from app.services.llm.client import LLMClient
from app.services.llm.llm_guard import guarded_json_call
from app.tools.graph_rag import GraphRagTool
from app.tools.hybrid_search import HybridSearchTool
from app.tools.memory_retrieval import MemoryRetrievalTool
from app.tools.multimodal_rag import MultimodalRagTool
from app.tools.semantic_cache import SemanticCache

logger = get_logger(__name__)

CONFIDENCE_THRESHOLD = 0.35

TOOL_ROUTE_TABLE: dict[str, list[str]] = {
    # 按 query_type 动态选择工具 —— 从不一次性调用全部工具。
    "factual": ["hybrid_search"],
    "relational": ["hybrid_search", "graph_rag"],  # P3: graph_rag 启用
    "visual": ["hybrid_search", "multimodal_rag"],  # P4: multimodal 启用
    "structural": ["hybrid_search", "sql_query"],
}

# ---------------------------------------------------------------------------
# 规则式理解（确定性兜底 / mock 路径）
# ---------------------------------------------------------------------------

_VISUAL_WORDS = ("路线", "示意图", "图纸", "图表", "流程图", "区域如何划分", "区域划分")
_RELATIONAL_WORDS = (
    "什么是", "征兆", "原因", "教训", "影响", "组成", "如何辨识",
    "如何纠正", "防止", "预防措施", "判断和处理", "关系", "区别", "关联",
)
_STRUCTURAL_WORDS = (
    "流程", "职责", "制度", "规定", "演练", "如何组织", "配置标准",
    "如何划分", "许可", "审批",
)


def classify_query_rules(query: str) -> str:
    """确定性 query_type 分类器（规则优先，LLM 辅助）。"""
    if any(w in query for w in _VISUAL_WORDS):
        return "visual"
    if any(w in query for w in _RELATIONAL_WORDS):
        return "relational"
    if any(w in query for w in _STRUCTURAL_WORDS):
        return "structural"
    return "factual"


class QueryUnderstanding(BaseModel):
    """understand node 的结构化输出。"""

    query_type: Literal["factual", "relational", "visual", "structural"]
    optimized_query: str = Field(min_length=1)
    sub_questions: list[str] = Field(min_length=1)


# ---------------------------------------------------------------------------
# 上下文容器
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class QAContext:
    """所有 node 共享的依赖。"""

    llm: LLMClient
    memory_tool: MemoryRetrievalTool
    search_tool: HybridSearchTool
    cache: SemanticCache
    graph_rag_tool: GraphRagTool | None = None
    multimodal_rag_tool: MultimodalRagTool | None = None
    faq_service: Any | None = None  # FAQ 永久缓存（None 则跳过该层）
    max_rounds: int = 2


# ---------------------------------------------------------------------------
# Nodes（节点）
# ---------------------------------------------------------------------------


def make_understand_node(ctx: QAContext):
    """Node 1：类型分类 + 结合历史的改写 + 问题分解。"""

    async def understand(state: dict) -> dict:
        raw = state["raw_query"]
        user_id = state["user_id"]
        session_id = state["session_id"]

        # 注入筛查（规则 + LLM 双保险）。
        blocked, reason = await screen_query(raw, ctx.llm)
        if blocked:
            logger.warning("Injection blocked for user=%s: %s", user_id, reason)
            refusal = "您的消息包含不允许的指令内容，请重新描述您的安全问题。"
            return {
                "generated_response": refusal,
                "query_type": "factual",
                "optimized_query": raw,
                "sub_questions": [raw],
                "confidence": 1.0,
                "sources": [],
                "cache_hit": True,  # 直接短路到 END
                "fused_context": "",
                "messages": [
                    {"role": "user", "content": raw},
                    {"role": "assistant", "content": refusal},
                ],
            }

        history = list(state.get("working_memory") or [])
        if not history:
            try:
                history = await ctx.memory_tool._wm.get_messages(
                    session_id, limit=6
                )
            except Exception:  # noqa: BLE001 — 历史是可选的
                history = []

        fallback = QueryUnderstanding(
            query_type=classify_query_rules(raw),  # type: ignore[arg-type]
            optimized_query=raw,
            sub_questions=[raw],
        )
        understanding: QueryUnderstanding
        if ctx.llm.mock_mode:
            understanding = fallback
        else:
            history_text = "\n".join(
                (
                    f"[此前对话摘要] {m['content'][:80]}"
                    if m["role"] == "summary"
                    else f"{m['role']}: {m['content'][:80]}"
                )
                for m in history[-4:]
            )
            understanding = await guarded_json_call(
                ctx.llm,
                [
                    {"role": "system", "content": QUERY_UNDERSTAND_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            f"## 对话历史\n{history_text or '（无）'}\n\n"
                            f"## 当前问题\n{raw}"
                        ),
                    },
                ],
                QueryUnderstanding,
                fallback=fallback,
            )

        planned = TOOL_ROUTE_TABLE.get(understanding.query_type, ["hybrid_search"])
        return {
            "query_type": understanding.query_type,
            "optimized_query": understanding.optimized_query,
            "sub_questions": understanding.sub_questions,
            "planned_tools": planned,
            "working_memory": history,
            "retrieval_round": 0,
            "max_rounds": ctx.max_rounds,
            "cache_hit": False,
        }

    return understand


def make_cache_lookup_node(ctx: QAContext):
    """Node 2：两级语义缓存（精确 -> 语义）。

    understand node 已设置的 ``cache_hit``（注入拦截）会在此处短路为
    空操作，并直接路由到 END。
    """

    async def cache_lookup(state: dict) -> dict:
        if state.get("cache_hit"):
            return {}
        entry = await ctx.cache.get(
            state["optimized_query"], state.get("cache_scope", "default")
        )
        if entry is None:
            return {"cache_hit": False}
        return {
            "cache_hit": True,
            "generated_response": entry.response,
            "sources": entry.sources,
            "confidence": 1.0,
            "fused_context": "(cache)",
        }

    return cache_lookup


def make_retrieve_memory_node(ctx: QAContext):
    """Node 3：情景 + 语义长期记忆检索。"""

    async def retrieve_memory(state: dict) -> dict:
        result = await ctx.memory_tool.run(
            user_id=state["user_id"],
            session_id=state["session_id"],
            query=state["optimized_query"],
        )
        return {"retrieved_memories": result.hits}

    return retrieve_memory


def make_plan_tools_node(ctx: QAContext):
    """Node 4：按已分类的 query_type 动态选择工具。"""

    async def plan_tools(state: dict) -> dict:
        qtype = state.get("query_type", "factual")
        planned = state.get("planned_tools") or TOOL_ROUTE_TABLE.get(
            qtype, ["hybrid_search"]
        )
        return {"planned_tools": planned}

    return plan_tools


def _execute_one(name: str, state: dict, ctx: QAContext) -> Any:
    """派发单个计划中的工具调用。"""
    if name == "hybrid_search":
        return ctx.search_tool.run(
            state["optimized_query"],
            doc_types=state.get("allowed_doc_types"),
        )
    if name == "graph_rag":
        if ctx.graph_rag_tool is None:
            return _empty()
        return ctx.graph_rag_tool.run(
            state["optimized_query"],
        )
    if name == "multimodal_rag":
        if ctx.multimodal_rag_tool is None:
            return _empty()
        return ctx.multimodal_rag_tool.run(
            state["optimized_query"],
        )
    if name == "sql_query":
        from app.tools.sql_query import SqlQueryTool

        return SqlQueryTool().run(
            "SELECT 1 AS placeholder"  # 结构化查询在 P5/P6 阶段接入
        )
    logger.warning("Unknown planned tool: %s", name)
    return _empty()


async def _empty() -> list[dict[str, Any]]:
    return []


def make_execute_tools_node(ctx: QAContext):
    """Node 5：并行运行全部计划中的工具（asyncio.gather）。"""

    async def execute_tools(state: dict) -> dict:
        planned = state.get("planned_tools") or ["hybrid_search"]
        span = lf.lf_start_span(
            None,
            "retrieval",
            metadata={
                "planned_tools": planned,
                "query": str(state.get("optimized_query", ""))[:120],
            },
        )
        results = await asyncio.gather(
            *[_execute_one(name, state, ctx) for name in planned],
            return_exceptions=True,
        )
        lf.lf_end_span(span)
        tool_results: dict[str, Any] = {}
        for name, res in zip(planned, results, strict=False):
            if isinstance(res, Exception):
                logger.warning("Tool '%s' failed: %s", name, res)
                tool_results[name] = []
            else:
                tool_results[name] = res
        return {"tool_results": tool_results}

    return execute_tools


def _top_kb_score(state: dict) -> float:
    hits = (state.get("tool_results") or {}).get("hybrid_search") or []
    return float(hits[0]["score"]) if hits else 0.0


def make_quality_gate_node(ctx: QAContext):
    """Node 6：置信度不足时改写并重试。"""

    async def quality_gate(state: dict) -> dict:
        score = _top_kb_score(state)
        has_memory = bool(state.get("retrieved_memories"))
        confidence = min(1.0, score * 1.25) if score else (0.5 if has_memory else 0.0)
        gate = {
            "confidence": round(confidence, 4),
            "retrieval_round": state.get("retrieval_round", 0),
        }
        if confidence >= CONFIDENCE_THRESHOLD:
            return gate

        round_no = state.get("retrieval_round", 0)
        if round_no >= state.get("max_rounds", ctx.max_rounds):
            return gate  # 轮次已用尽 —— 就手头内容融合

        # 改写：用子问题扩展以放宽检索网。
        subs = state.get("sub_questions") or []
        rewrite = state["optimized_query"]
        extra = next((s for s in subs if s and s != rewrite), None)
        if extra:
            rewrite = f"{rewrite} {extra}"
        elif ctx.llm.mock_mode:
            rewrite = f"{rewrite} 详细规定 操作要求"
        else:
            rewritten = await guarded_json_call(
                ctx.llm,
                [
                    {
                        "role": "system",
                        "content": "把问题改写为更适合知识库检索的查询，只输出改写后的问题文本。",
                    },
                    {"role": "user", "content": rewrite},
                ],
                _Rewrite,
                fallback=_Rewrite(rewritten=f"{rewrite} 详细要求"),
            )
            rewrite = rewritten.rewritten
        logger.info(
            "Quality gate retry round=%s -> rewrite: %s", round_no, rewrite[:40]
        )
        return {
            "confidence": round(confidence, 4),
            "optimized_query": rewrite,
            "retrieval_round": round_no + 1,
        }

    return quality_gate


class _Rewrite(BaseModel):
    rewritten: str


class FuseOutput(BaseModel):
    """融合 LLM 调用产出的结构化答案。"""

    response: str


def _trim(text: str, limit: int = 200) -> str:
    return text if len(text) <= limit else text[:limit] + "…"


def build_fused_context(state: dict) -> tuple[str, list[dict[str, Any]]]:
    """编号上下文块 + 可引用的来源列表。"""
    tool_results = state.get("tool_results") or {}
    hits = tool_results.get("hybrid_search") or []
    sources: list[dict[str, Any]] = []
    blocks: list[str] = []
    for i, hit in enumerate(hits[:5], start=1):
        blocks.append(f"[{i}] {_trim(str(hit.get('text', '')))}")
        sources.append(
            {
                "doc_type": str(hit.get("doc_type", "")),
                "score": float(hit.get("score", 0.0)),
                "text": str(hit.get("text", "")),
                "doc_id": hit.get("doc_id"),
                "chunk_id": hit.get("chunk_id"),
                "position": hit.get("position"),
                "access_level": access_level_of(str(hit.get("doc_type", ""))),
            }
        )
    # GraphRAG 结果：社区摘要作为上下文块附加。
    graph_hits = tool_results.get("graph_rag") or []
    if graph_hits:
        graph_lines: list[str] = []
        for _j, gh in enumerate(graph_hits[:5], start=1):
            entity = gh.get("entity", "")
            etype = gh.get("type", "")
            summary = gh.get("community_summary", "")
            hops = gh.get("hops", 0)
            label = f"{entity}({etype})" if etype else entity
            graph_lines.append(
                f"- {label} [跳数={hops}] {summary}"
            )
        blocks.append("[图知识] " + "\n".join(graph_lines))
    # 多模态 RAG 结果：页级视觉上下文块附加。
    visual_hits = tool_results.get("multimodal_rag") or []
    if visual_hits:
        visual_lines: list[str] = []
        for vh in visual_hits[:5]:
            desc = vh.get("description", "")
            page = vh.get("page_num", "?")
            score = vh.get("score", 0.0)
            visual_lines.append(
                f"- [页面{page}] score={score:.2f} {_trim(desc, 150)}"
            )
        blocks.append("[图表/图纸] " + "\n".join(visual_lines))
    memories = state.get("retrieved_memories") or []
    if memories:
        mem_lines = [
            f"- {m['content'][:80]}（{m['source']}记忆, {m['memory_type'] or 'summary'}）"
            for m in memories[:3]
        ]
        blocks.append("[记忆] " + "\n".join(mem_lines))
    return "\n\n".join(blocks), sources


def mock_answer(
    question: str, sources: list[dict[str, Any]], memories: list[dict[str, Any]]
) -> str:
    """由融合上下文拼装的确定性离线答案（Markdown 格式）。"""
    if not sources and not memories:
        return (
            "**当前知识库中未检索到与您问题直接相关的资料。**\n\n"
            "建议：\n"
            "1. 查阅对应岗位操作规程\n"
            "2. 咨询现场安全管理人员"
        )
    parts = [f"关于「{question}」，依据检索到的资料："]
    for i, src in enumerate(sources[:2], start=1):
        parts.append(f"> {_trim(src['text'], 160)}[{i}]")
    if memories:
        parts.append(
            f"结合您的历史记录：{_trim(str(memories[0]['content']), 80)}"
        )
    parts.append("---\n*以上内容摘自安全知识库，请以现行有效版本规程为准。*")
    return "\n\n".join(parts)


def make_fuse_respond_node(ctx: QAContext):
    """Node 7：融合上下文、带引用生成，并落盘缓存 / 记忆。"""

    async def fuse_respond(state: dict) -> dict:
        fused, sources = build_fused_context(state)
        memories = state.get("retrieved_memories") or []
        question = state["optimized_query"]

        if ctx.llm.mock_mode:
            answer = mock_answer(question, sources, memories)
        else:
            fallback_answer = mock_answer(question, sources, memories)
            mem_block = ""
            if memories:
                mem_lines = "\n".join(
                    f"- {m['content'][:80]}" for m in memories[:3]
                )
                mem_block = f"\n\n## 相关记忆\n{mem_lines}"
            context_text = fused or "（无检索结果）"
            user_prompt = FUSE_ANSWER_USER.format(
                context=context_text, question=question
            )
            guarded = await guarded_json_call(
                ctx.llm,
                [
                    {"role": "system", "content": FUSE_ANSWER_SYSTEM},
                    {
                        "role": "user",
                        "content": f"{user_prompt}{mem_block}",
                    },
                ],
                FuseOutput,
                max_tokens=2048,
                fallback=FuseOutput(response=fallback_answer),
            )
            answer = guarded.response

        # 落盘：会话消息 + 答案缓存（尽力而为，不阻塞主流程）。
        session_id = state["session_id"]
        try:
            await ctx.memory_tool._wm.add_message(
                session_id, "user", state["raw_query"]
            )
            await ctx.memory_tool._wm.add_message(
                session_id, "assistant", answer
            )
            await ctx.cache.put(
                state["raw_query"], answer, sources, state.get("cache_scope", "default")
            )
        except Exception as exc:  # noqa: BLE001 — 持久化是尽力而为
            logger.warning("Post-response persistence failed: %s", exc)

        return {
            "fused_context": fused,
            "generated_response": answer,
            "sources": sources,
            "messages": [
                {"role": "user", "content": state["raw_query"]},
                {"role": "assistant", "content": answer},
            ],
        }

    return fuse_respond


def route_after_cache(state: dict) -> str:
    """条件边：缓存命中则短路到 END，否则进入 FAQ 层。"""
    from langgraph.graph import END

    return END if state.get("cache_hit") else "faq_lookup"


def make_faq_lookup_node(ctx: QAContext):
    """Node 2.5：FAQ 永久缓存匹配（Redis miss 后、完整 RAG 之前）。

    命中精校 FAQ 时直接返回答案（标记 cache_hit 走 END 短路），
    并回写 Redis 语义缓存加速后续同类问题；未命中继续走 RAG。
    """
    from langgraph.graph import END

    async def faq_lookup(state: dict) -> dict:
        if state.get("cache_hit") or ctx.faq_service is None:
            return {}
        hit = await ctx.faq_service.search(state["optimized_query"])
        if hit is None:
            return {"faq_hit": False}
        sources = [
            {
                "doc_type": "FAQ",
                "score": round(hit.score, 4),
                "text": f"Q: {hit.question}\nA: {hit.answer}",
                "doc_id": None,
                "chunk_id": f"faq-{hit.id}",
                "position": None,
                "access_level": "public",
            }
        ]
        # 回写 Redis 语义缓存：同类问题下次直接命中第一级
        try:
            await ctx.cache.put(
                state["optimized_query"],
                hit.answer,
                sources,
                state.get("cache_scope", "default"),
            )
        except Exception:  # noqa: BLE001 —— 回写失败不影响响应
            logger.warning("FAQ cache write-back failed")
        await ctx.faq_service.incr_hit(hit.id)
        logger.info("FAQ HIT id=%s score=%.3f q=%s", hit.id, hit.score,
                    state["optimized_query"][:40])
        return {
            "faq_hit": True,
            "cache_hit": True,
            "answer": hit.answer,
            "generated_response": hit.answer,
            "sources": sources,
        }

    def route_after_faq(state: dict) -> str:
        from langgraph.graph import END as _END

        return _END if state.get("faq_hit") else "retrieve_memory"

    return faq_lookup, route_after_faq


def route_after_gate(state: dict) -> str:
    """条件边：重试执行，否则进入融合。"""
    confidence = state.get("confidence", 0.0)
    if confidence < CONFIDENCE_THRESHOLD and state.get(
        "retrieval_round", 0
    ) < state.get("max_rounds", 2):
        return "execute_tools"
    return "fuse_respond"


def trace_note() -> str:
    """当前 trace id（供 API 层做可观测性使用）。"""
    return get_trace_id()
