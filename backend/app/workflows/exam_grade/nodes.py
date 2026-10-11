"""判卷工作流的 2 个 LangGraph node。

顺序（prompt §P5）：
    grade_objective -> grade_subjective

客观题（单选/多选/判断）：精确匹配计分。
主观题（简答）：基于评分标准的 RAG 增强评分。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from app.core.logger import get_logger
from app.models.exam import GradedBy
from app.prompts.exam import (
    EXAM_GRADE_SUBJECTIVE_SYSTEM,
    EXAM_GRADE_SUBJECTIVE_USER,
)
from app.services.llm.client import LLMClient
from app.services.llm.llm_guard import guarded_json_call
from app.tools.hybrid_search import HybridSearchTool

logger = get_logger(__name__)


@dataclass(slots=True)
class ExamGradeContext:
    """所有判卷 node 共享的依赖。"""

    llm: LLMClient
    search_tool: HybridSearchTool


# ---------------------------------------------------------------------------
# 主观题评分的结构化输出
# ---------------------------------------------------------------------------


class SubjectiveGradeResult(BaseModel):
    """单道主观题答案的 LLM 输出。"""

    score: float = Field(ge=0)
    max_score: float
    rubric_scores: dict[str, float] = Field(default_factory=dict)
    reason: str = ""
    reference_snippets: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Node 1：客观题判分（精确匹配）
# ---------------------------------------------------------------------------


def make_grade_objective_node(ctx: ExamGradeContext):
    """Node 1：单选 / 多选 / 判断题的精确匹配计分。"""

    async def grade_objective(state: dict) -> dict:
        questions = state.get("questions", [])
        answers = state.get("answers", [])
        question_scores = state.get("question_scores", {})

        answer_map: dict[int, str] = {
            a["question_id"]: a["user_answer"] for a in answers
        }
        graded: list[dict[str, Any]] = []

        for q in questions:
            qtype = q.get("question_type", "")
            if qtype == "short_answer":
                continue  # 主观题 —— 在 node 2 中评分

            qid = q["id"]
            user_ans = answer_map.get(qid, "").strip()
            correct_ans = q.get("answer", "").strip()
            max_score = float(question_scores.get(str(qid), 5.0))

            # 归一化后比较。
            is_correct = _exact_match(user_ans, correct_ans, qtype)
            score = max_score if is_correct else 0.0
            detail = (
                f"正确答案: {correct_ans}；用户答案: {user_ans}；"
                f"{'正确' if is_correct else '错误'}"
            )
            graded.append({
                "question_id": qid,
                "user_answer": user_ans,
                "score": score,
                "grading_detail": detail,
                "graded_by": GradedBy.AUTO,
            })
            logger.info("Objective grade qid=%s: %s/%s", qid, score, max_score)

        return {"graded_answers": graded}

    return grade_objective


def _exact_match(user: str, correct: str, qtype: str) -> bool:
    """对客观题答案做归一化并比较。"""
    # 归一化：去空白、选项字母转大写、去除空格。
    def normalize(s: str) -> str:
        return "".join(c.upper() for c in s if c.isalnum())

    nu = normalize(user)
    nc = normalize(correct)
    if qtype == "multiple":
        # 多选题不区分顺序（如 "AB" == "BA"）。
        return set(nu) == set(nc)
    if qtype == "judge":
        # 接受 对/错、T/F、true/false、是/否
        truthy = {"对", "T", "TRUE", "是", "Y", "YES"}
        falsy = {"错", "F", "FALSE", "否", "N", "NO"}
        return (nu in truthy and nc in truthy) or (nu in falsy and nc in falsy)
    return nu == nc


# ---------------------------------------------------------------------------
# Node 2：主观题评分（RAG + 评分标准）
# ---------------------------------------------------------------------------


def make_grade_subjective_node(ctx: ExamGradeContext):
    """Node 2：简答题的 RAG 增强评分。

    先从知识库检索参考上下文，再让 LLM 依据评分标准打分，并给出引用
    参考内容的评分理由。
    """

    async def grade_subjective(state: dict) -> dict:
        questions = state.get("questions", [])
        answers = state.get("answers", [])
        question_scores = state.get("question_scores", {})
        existing = list(state.get("graded_answers", []))

        answer_map: dict[int, str] = {
            a["question_id"]: a["user_answer"] for a in answers
        }

        for q in questions:
            if q.get("question_type") != "short_answer":
                continue

            qid = q["id"]
            user_ans = answer_map.get(qid, "")
            correct_ans = q.get("answer", "")
            stem = q.get("stem", "")
            max_score = float(question_scores.get(str(qid), 20.0))

            # 检索参考知识用于接地（grounding）。
            hits = await ctx.search_tool.run(stem)
            context = "\n\n".join(
                h.get("text", "")[:400] for h in hits[:4] if h.get("text")
            ) or "（无检索结果）"

            # 构建评分标准（关键评分维度）。
            rubric = (
                "1. 关键知识点完整性 (40%): 答案是否包含核心知识点。\n"
                "2. 正确性 (30%): 技术内容是否准确。\n"
                "3. 条理清晰度 (20%): 表述是否条理清晰、可操作。\n"
                "4. 完整度 (10%): 是否覆盖题目要求的全部要点。"
            )

            # LLM 评分或 mock 兜底。
            if ctx.llm.mock_mode:
                score, reason = _mock_grade(user_ans, correct_ans, max_score)
            else:
                try:
                    user_prompt = EXAM_GRADE_SUBJECTIVE_USER.format(
                        stem=stem,
                        reference_answer=correct_ans,
                        user_answer=user_ans,
                        context=context,
                        rubric=rubric,
                        max_score=max_score,
                    )
                    fallback = SubjectiveGradeResult(
                        score=max_score * 0.5,
                        max_score=max_score,
                        reason="(mock降级) 无法调用LLM评分，给50%基准分",
                    )
                    result = await guarded_json_call(
                        ctx.llm,
                        [
                            {"role": "system", "content": EXAM_GRADE_SUBJECTIVE_SYSTEM},
                            {"role": "user", "content": user_prompt},
                        ],
                        SubjectiveGradeResult,
                        fallback=fallback,
                    )
                    score = min(result.score, max_score)
                    reason = result.reason or "(无评分理由)"
                except Exception:  # noqa: BLE001
                    score, reason = _mock_grade(user_ans, correct_ans, max_score)

            detail = f"评分理由: {reason}"
            existing.append({
                "question_id": qid,
                "user_answer": user_ans,
                "score": score,
                "grading_detail": detail,
                "graded_by": GradedBy.AUTO,
            })
            logger.info("Subjective grade qid=%s: %s/%s", qid, score, max_score)

        # 计算总分。
        total = sum(a["score"] for a in existing)

        # 分析：基于知识点标签提取薄弱/掌握点。
        weak, strong = _analyze(
            questions, existing, question_scores
        )

        return {
            "graded_answers": existing,
            "total_score": total,
            "weak_points": weak,
            "strong_points": strong,
        }

    return grade_subjective


def _mock_grade(
    user_ans: str, correct_ans: str, max_score: float
) -> tuple[float, str]:
    """确定性兜底：关键词重合率。"""
    if not user_ans.strip():
        return 0.0, "用户未作答，0分。"
    user_words = set(user_ans)
    correct_words = set(correct_ans)
    if not correct_words:
        return max_score * 0.5, "(mock) 参考答案为空，给50%基准分。"
    overlap = len(user_words & correct_words) / len(correct_words)
    score = max_score * overlap
    reason = (
        f"(mock降级) 关键词重合率 {overlap:.0%}，"
        f"得分 {score:.1f}/{max_score}。"
    )
    return round(score, 1), reason


def _analyze(
    questions: list[dict[str, Any]],
    graded: list[dict[str, Any]],
    question_scores: dict[str, float],
) -> tuple[list[str], list[str]]:
    """基于已判分答案生成薄弱/掌握点分析。"""
    q_map = {q["id"]: q for q in questions}
    weak: list[str] = []
    strong: list[str] = []
    for ga in graded:
        qid = ga["question_id"]
        q = q_map.get(qid, {})
        tags = q.get("knowledge_tags") or []
        max_score = float(question_scores.get(str(qid), 5.0))
        ratio = ga["score"] / max_score if max_score > 0 else 0
        if ratio < 0.6:
            weak.extend(tags)
        elif ratio >= 0.8:
            strong.extend(tags)
    # 去重。
    return list(set(weak)), list(set(strong))
