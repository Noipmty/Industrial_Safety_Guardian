"""出题 LangGraph 工作流的 ExamGenState。"""

from __future__ import annotations

from typing import Any, TypedDict


class ExamGenState(TypedDict, total=False):
    """流经出题 graph 的共享状态。"""

    # 请求参数
    user_id: int
    position: str
    question_types: list[str]
    num_questions: int
    knowledge_tags: list[str]
    type_counts: dict[str, int]

    # 意图识别
    raw_query: str
    is_exam_intent: bool
    intent_reason: str

    # 检索上下文
    context: str
    retrieved_chunks: list[dict[str, Any]]

    # 生成的题目
    generated_questions: list[dict[str, Any]]

    # 质量检查
    quality_passed: bool
    quality_issues: list[str]
    quality_suggestions: list[str]

    # 输出
    exam_id: int
    error: str
