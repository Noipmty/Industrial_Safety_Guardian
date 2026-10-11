"""出题工作流的 3 个 LangGraph node。

顺序（prompt §P5）：
    intent_detect -> generate_questions -> quality_check

意图识别先用规则（可识别否定）+ LLM 确认。题目生成产出经 Pydantic
校验的结构化 JSON，随后落库。质量检查校验知识点覆盖与难度分布。
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from app.core.logger import get_logger
from app.models.exam import Exam, ExamStatus, Question, QuestionType
from app.prompts.exam import (
    _EXAM_INTENT_LLM_SYSTEM,
    EXAM_GENERATE_SYSTEM,
    EXAM_GENERATE_USER,
    EXAM_QUALITY_CHECK_SYSTEM,
    detect_exam_intent_rules,
)
from app.services.llm.client import LLMClient
from app.services.llm.llm_guard import guarded_json_call
from app.tools.hybrid_search import HybridSearchTool

logger = get_logger(__name__)

# 各题型的默认分值分配。
DEFAULT_SCORES: dict[str, float] = {
    "single": 5.0,
    "multiple": 10.0,
    "judge": 5.0,
    "short_answer": 20.0,
}


@dataclass(slots=True)
class ExamGenContext:
    """所有出题 node 共享的依赖。"""

    llm: LLMClient
    search_tool: HybridSearchTool
    session_factory: Any  # async_sessionmaker[AsyncSession]


# ---------------------------------------------------------------------------
# 结构化输出
# ---------------------------------------------------------------------------


class GeneratedQuestion(BaseModel):
    """单道 LLM 生成的题目（落库前）。"""

    question_type: str
    stem: str = Field(min_length=1)
    options: list[str] | None = None
    answer: str = Field(min_length=1)
    explanation: str | None = None
    knowledge_tags: list[str] | None = None
    difficulty: int = Field(default=3, ge=1, le=5)
    source_chunk_id: str | None = None


class QualityCheckResult(BaseModel):
    """质量检查输出。"""

    passed: bool
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Node 1：意图识别（可识别否定）
# ---------------------------------------------------------------------------


def make_intent_detect_node(ctx: ExamGenContext):
    """Node 1：判断用户是否想要出题（可识别否定）。

    先走规则，再由 LLM 确认。``"不要出题"`` 必须被识别为否定。
    当从 API 端点调用（state 中 ``intent_confirmed=True``）时，该 node
    直接放行。
    """

    async def intent_detect(state: dict) -> dict:
        # API 端点已确认意图 —— 直接放行。
        if state.get("intent_confirmed"):
            return {"is_exam_intent": True, "intent_reason": "API confirmed"}

        raw = state.get("raw_query", "")
        if not raw:
            return {"is_exam_intent": True, "intent_reason": "no query to screen"}

        # 规则判定（可识别否定）。
        is_intent, reason = detect_exam_intent_rules(raw)
        if not is_intent and "否定" in reason:
            logger.info("Exam intent negated: %s", reason)
            return {"is_exam_intent": False, "intent_reason": reason}

        # LLM 确认（双保险）—— 仅在规则结果不明确时执行。
        if not ctx.llm.mock_mode:
            try:
                class IntentResult(BaseModel):
                    is_exam_intent: bool
                    reason: str

                result = await guarded_json_call(
                    ctx.llm,
                    [
                        {"role": "system", "content": _EXAM_INTENT_LLM_SYSTEM},
                        {"role": "user", "content": raw},
                    ],
                    IntentResult,
                    fallback=IntentResult(is_exam_intent=is_intent, reason=reason),
                )
                return {
                    "is_exam_intent": result.is_exam_intent,
                    "intent_reason": result.reason,
                }
            except Exception:  # noqa: BLE001, S110 — 降级为规则结果
                pass

        return {"is_exam_intent": is_intent, "intent_reason": reason}

    return intent_detect


# ---------------------------------------------------------------------------
# Node 2：题目生成（结构化 + RAG 支撑）
# ---------------------------------------------------------------------------


def make_generate_questions_node(ctx: ExamGenContext):
    """Node 2：检索参考知识、生成结构化题目，经 Pydantic 校验后
    落库。"""

    async def generate_questions(state: dict) -> dict:
        position = state["position"]
        question_types = state["question_types"]
        num_questions = state["num_questions"]
        knowledge_tags = state.get("knowledge_tags") or []
        type_counts: dict[str, int] = state.get("type_counts") or {}

        # 检索参考知识用于接地（grounding）。
        query = " ".join(knowledge_tags) if knowledge_tags else f"{position} 安全生产 考试"
        hits = await ctx.search_tool.run(query)
        context = "\n\n".join(
            h.get("text", "")[:500] for h in hits[:6] if h.get("text")
        ) or "（无检索结果，基于通用安全知识出题）"

        # LLM 生成（或确定性 mock）。
        if ctx.llm.mock_mode:
            questions = _mock_generate(question_types, num_questions, position)
            questions = _rebalance(questions, type_counts)
        else:
            type_counts_desc = (
                "、".join(f"{k} {v} 道" for k, v in type_counts.items())
                if type_counts
                else "不限（由你合理分配）"
            )
            user_prompt = EXAM_GENERATE_USER.format(
                position=position,
                question_types="、".join(question_types),
                num_questions=num_questions,
                type_counts=type_counts_desc,
                knowledge_tags="、".join(knowledge_tags) if knowledge_tags else "不限",
                context=context,
            )
            fallback = _rebalance(
                _mock_generate(question_types, num_questions, position), type_counts
            )
            try:
                resp = await ctx.llm.chat(
                    [
                        {"role": "system", "content": EXAM_GENERATE_SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.7,
                    max_tokens=4096,
                )
                raw_data = resp.json()
                if isinstance(raw_data, list):
                    questions = [
                        GeneratedQuestion.model_validate(q) for q in raw_data
                    ]
                    questions = _rebalance(questions, type_counts)
                else:
                    questions = fallback
            except Exception:  # noqa: BLE001 — 降级为 mock
                logger.warning("LLM question generation failed, using mock")
                questions = fallback

        # 将题目 + 试卷写入数据库。
        exam_id = await _persist_exam(ctx, state, questions, question_types)
        logger.info("Exam %d generated with %d questions", exam_id, len(questions))

        return {
            "generated_questions": [q.model_dump() for q in questions],
            "context": context,
            "retrieved_chunks": hits[:6],
            "exam_id": exam_id,
        }

    return generate_questions


def _rebalance(
    questions: list[GeneratedQuestion], type_counts: dict[str, int]
) -> list[GeneratedQuestion]:
    """按 type_counts 精确校正题型数量：多余裁剪、不足补 mock 同型题。"""
    if not type_counts:
        return questions

    result: list[GeneratedQuestion] = []
    for qtype, count in type_counts.items():
        pool = [q for q in questions if q.question_type == qtype]
        result.extend(pool[:count])
        # 不足时用 mock 库补齐同型题。
        while len([q for q in result if q.question_type == qtype]) < count:
            filler = _mock_generate([qtype], 1, "司钻")[0]
            filler.stem = f"（补充题）{filler.stem}"
            result.append(filler)

    # 校验总数一致（防止 type_counts 遗漏题型导致多题）。
    expected = sum(type_counts.values())
    return result[:expected] if len(result) > expected else result


async def _persist_exam(
    ctx: ExamGenContext,
    state: dict,
    questions: list[GeneratedQuestion],
    question_types: list[str],
) -> int:
    """插入题目与试卷记录，返回新试卷 ID。"""
    async with ctx.session_factory() as session:
        question_ids_scores: list[dict[str, Any]] = []
        total_score = Decimal("0")
        for q in questions:
            qtype = QuestionType(q.question_type)
            row = Question(
                question_type=qtype,
                stem=q.stem,
                options=q.options,
                answer=q.answer,
                explanation=q.explanation,
                knowledge_tags=q.knowledge_tags,
                difficulty=q.difficulty,
                source_chunk_id=q.source_chunk_id,
            )
            session.add(row)
            await session.flush()
            score = Decimal(str(DEFAULT_SCORES.get(q.question_type, 5.0)))
            question_ids_scores.append({"id": row.id, "score": float(score)})
            total_score += score

        exam = Exam(
            user_id=state["user_id"],
            position=state["position"],
            question_ids=question_ids_scores,
            status=ExamStatus.CREATED,
            total_score=total_score,
            time_limit=3600,
        )
        session.add(exam)
        await session.commit()
        return exam.id


def _mock_generate(
    question_types: list[str], num: int, position: str
) -> list[GeneratedQuestion]:
    """mock / 离线模式下的确定性兜底题目。"""
    bank: list[GeneratedQuestion] = [
        GeneratedQuestion(
            question_type="single",
            stem=f"钻开油气层前{position}应确认的最重要参数是？",
            options=["井底压力", "钻井液密度", "套管深度", "钻头尺寸"],
            answer="A",
            explanation="井底压力是井控的核心参数，必须保持井底压力 ≥ 地层孔隙压力。",
            knowledge_tags=["井控", "井底压力"],
            difficulty=2,
        ),
        GeneratedQuestion(
            question_type="multiple",
            stem="发生溢流的征兆包括（多选）？",
            options=["钻井液池液面升高", "泵压下降", "出口流量增大", "钻速突然加快"],
            answer="ABC",
            explanation="溢流征兆包括液面升高、流量增大、泵压变化等，需立即实施井控作业。",
            knowledge_tags=["溢流", "井控征兆"],
            difficulty=3,
        ),
        GeneratedQuestion(
            question_type="judge",
            stem="井控作业中，压井前必须先关井以求得关井立管压力。",
            answer="对",
            explanation="关井是压井作业的第一步，通过关井立压和套压判断地层压力。",
            knowledge_tags=["压井", "关井"],
            difficulty=2,
        ),
        GeneratedQuestion(
            question_type="short_answer",
            stem=f"请简述{position}在井控中的主要职责。",
            answer="协助司钻监控井控参数，发现溢流征兆立即报告；参与关井和压井作业；维护井控设备。",
            explanation="各岗位井控职责是安全培训的重点内容。",
            knowledge_tags=["井控", "岗位职责"],
            difficulty=4,
        ),
        GeneratedQuestion(
            question_type="single",
            stem="H₂S气体浓度超过多少 ppm 时必须佩戴正压式空气呼吸器？",
            options=["5 ppm", "10 ppm", "15 ppm", "20 ppm"],
            answer="B",
            explanation="H₂S浓度超过 10 ppm 必须佩戴正压式空气呼吸器。",
            knowledge_tags=["硫化氢", "防护"],
            difficulty=3,
        ),
    ]
    # 按要求的题型过滤；无匹配则使用全部。
    filtered = [q for q in bank if q.question_type in question_types] or bank
    result: list[GeneratedQuestion] = []
    for i in range(num):
        result.append(filtered[i % len(filtered)])
    return result


# ---------------------------------------------------------------------------
# Node 3：质量检查（知识点覆盖 + 难度分布）
# ---------------------------------------------------------------------------


def make_quality_check_node(ctx: ExamGenContext):
    """Node 3：校验知识点覆盖与难度分布。"""

    async def quality_check(state: dict) -> dict:
        questions = state.get("generated_questions", [])
        question_types = state.get("question_types", [])

        # 先做确定性检查。
        issues: list[str] = []

        # 题型匹配检查。
        for q in questions:
            if q["question_type"] not in question_types:
                issues.append(f"题型不匹配: {q['question_type']} 不在要求列表内")

        # 难度分布检查。
        easy = sum(1 for q in questions if q.get("difficulty", 3) <= 2)
        medium = sum(1 for q in questions if q.get("difficulty", 3) == 3)
        hard = sum(1 for q in questions if q.get("difficulty", 3) >= 4)
        total = len(questions)
        if total > 0:
            easy_ratio = easy / total
            if easy_ratio < 0.2 or easy_ratio > 0.6:
                issues.append(
                    f"难度分布不均: 简单{easy}题({easy_ratio:.0%}) "
                    f"中等{medium}题 困难{hard}题"
                )

        # 知识点覆盖检查。
        tags: list[str] = []
        for q in questions:
            tags.extend(q.get("knowledge_tags") or [])
        unique_tags = set(tags)
        if total >= 4 and len(unique_tags) < total * 0.5:
            issues.append(
                f"知识点覆盖不足: {len(unique_tags)}个唯一知识点 / {total}题"
            )

        # LLM 质量检查（可选，可用时才执行）。
        if ctx.llm.mock_mode:
            passed = len(issues) == 0
            return {
                "quality_passed": passed,
                "quality_issues": issues,
                "quality_suggestions": [] if passed else ["建议重新生成"],
            }

        try:
            questions_json = str(questions[:10])
            user_msg = f"## 题目列表\n{questions_json}\n\n## 要求题型\n{question_types}"
            result = await guarded_json_call(
                ctx.llm,
                [
                    {"role": "system", "content": EXAM_QUALITY_CHECK_SYSTEM},
                    {"role": "user", "content": user_msg},
                ],
                QualityCheckResult,
                fallback=QualityCheckResult(
                    passed=len(issues) == 0, issues=issues
                ),
            )
            all_issues = issues + result.issues
            return {
                "quality_passed": result.passed and len(issues) == 0,
                "quality_issues": all_issues,
                "quality_suggestions": result.suggestions,
            }
        except Exception:  # noqa: BLE001
            passed = len(issues) == 0
            return {
                "quality_passed": passed,
                "quality_issues": issues,
                "quality_suggestions": [] if passed else ["建议重新生成"],
            }

    return quality_check


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------


def route_after_intent(state: dict) -> str:
    """若非出题意图，直接短路到 END。"""
    if state.get("is_exam_intent", True):
        return "generate_questions"
    return "__end__"
