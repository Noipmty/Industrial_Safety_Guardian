"""判卷 LangGraph 工作流的 ExamGradeState。"""

from __future__ import annotations

from typing import Any, TypedDict


class ExamGradeState(TypedDict, total=False):
    """流经判卷 graph 的共享状态。"""

    # 试卷标识
    exam_id: int
    user_id: int

    # 题目 + 答案（从数据库加载）
    questions: list[dict[str, Any]]  # 完整 Question 行（含答案）
    answers: list[dict[str, Any]]  # 提交的答案 {question_id, user_answer}
    question_scores: dict[str, float]  # {question_id: 满分}

    # 判分结果
    graded_answers: list[dict[str, Any]]  # {question_id, score, grading_detail, graded_by}
    total_score: float

    # 分析
    weak_points: list[str]
    strong_points: list[str]
