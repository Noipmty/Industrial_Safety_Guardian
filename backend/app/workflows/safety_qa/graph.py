"""安全问答工作流的 LangGraph 组装（7 个 node，固定顺序）。"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.workflows.safety_qa.nodes import (
    QAContext,
    make_cache_lookup_node,
    make_execute_tools_node,
    make_faq_lookup_node,
    make_fuse_respond_node,
    make_plan_tools_node,
    make_quality_gate_node,
    make_retrieve_memory_node,
    make_understand_node,
    route_after_cache,
    route_after_gate,
)
from app.workflows.safety_qa.state import AgentState


def build_safety_qa_graph(ctx: QAContext):
    """编译 QA graph：

    understand -> cache_lookup --hit--> END
                     |miss
                     v
                faq_lookup --hit--> END
                     |miss
                     v
              retrieve_memory -> plan_tools -> execute_tools
                     ^                              |
                     |                              v
                     +---- retry ---- quality_gate --+--ok--> fuse_respond -> END
    """
    builder = StateGraph(AgentState)
    builder.add_node("understand", make_understand_node(ctx))
    builder.add_node("cache_lookup", make_cache_lookup_node(ctx))
    faq_node, route_after_faq = make_faq_lookup_node(ctx)
    builder.add_node("faq_lookup", faq_node)
    builder.add_node("retrieve_memory", make_retrieve_memory_node(ctx))
    builder.add_node("plan_tools", make_plan_tools_node(ctx))
    builder.add_node("execute_tools", make_execute_tools_node(ctx))
    builder.add_node("quality_gate", make_quality_gate_node(ctx))
    builder.add_node("fuse_respond", make_fuse_respond_node(ctx))

    builder.add_edge(START, "understand")
    builder.add_edge("understand", "cache_lookup")
    builder.add_conditional_edges(
        "cache_lookup",
        route_after_cache,
        {END: END, "faq_lookup": "faq_lookup"},
    )
    builder.add_conditional_edges(
        "faq_lookup",
        route_after_faq,
        {END: END, "retrieve_memory": "retrieve_memory"},
    )
    builder.add_edge("retrieve_memory", "plan_tools")
    builder.add_edge("plan_tools", "execute_tools")
    builder.add_edge("execute_tools", "quality_gate")
    builder.add_conditional_edges(
        "quality_gate",
        route_after_gate,
        {"execute_tools": "execute_tools", "fuse_respond": "fuse_respond"},
    )
    builder.add_edge("fuse_respond", END)
    return builder.compile()
