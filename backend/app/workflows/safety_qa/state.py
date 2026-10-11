"""安全问答 LangGraph 工作流的 AgentState。

prompt §P2 中的每个字段都在（不允许删除）。字段默认被覆盖（后写
优先）；``messages`` 为累加。
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


class AgentState(TypedDict, total=False):
    """流经 7 节点 QA graph 的共享状态。"""

    # 会话标识
    messages: Annotated[list[dict[str, str]], operator.add]
    session_id: str
    user_id: int
    user_position: str

    # 查询理解
    raw_query: str
    optimized_query: str
    sub_questions: list[str]
    query_type: str  # factual | relational | visual | structural

    # 缓存 / 记忆
    cache_hit: bool
    faq_hit: bool  # FAQ 永久缓存命中（跳过完整 RAG）
    cache_scope: str  # 语义缓存视图桶（按角色权限隔离）
    working_memory: list[dict[str, str]]  # 用于改写上下文的近期对话轮
    retrieved_memories: list[dict[str, Any]]

    # 文档权限：允许检索的文档类型（None = 全库不限，仅管理员）
    allowed_doc_types: list[str] | None

    # 工具编排
    planned_tools: list[str]
    tool_results: dict[str, Any]
    retrieval_round: int
    max_rounds: int

    # 融合 / 输出
    fused_context: str
    generated_response: str
    confidence: float
    sources: list[dict[str, Any]]
