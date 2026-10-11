"""考试接口：生成 / 列表 / 详情 / 提交（幂等）/ 成绩。

提交幂等性：Redis ``exam:lock:{exam_id}`` SETNX + 数据库唯一约束
``uq_exam_question``（exam_answers 的 exam_id, question_id）。
重复提交会返回已有的判分结果。
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core import langfuse as lf
from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import ConflictError, NotFoundError, PermissionError_
from app.core.logger import get_logger
from app.models.exam import (
    Exam,
    ExamAnswer,
    ExamStatus,
    GradedBy,
    Question,
)
from app.schemas.exam import (
    ExamDetail,
    ExamGenerateRequest,
    ExamGenerateResponse,
    ExamListItem,
    ExamQuestion,
    ExamResult,
    ExamResultAnalysis,
    ExamSubmitRequest,
    ExamSubmitResponse,
    GradedAnswer,
)
from app.workflows.exam_generate.service import get_exam_gen_service
from app.workflows.exam_grade.service import get_exam_grade_service
from app.workflows.safety_qa.service import get_qa_service

logger = get_logger(__name__)
router = APIRouter(prefix="/exam", tags=["考试"])

LOCK_TTL = 300  # 提交锁 5 分钟


def _score_map(exam: Exam) -> dict[str, float]:
    """把 question_ids JSON 解析为 {question_id: score}。"""
    result: dict[str, float] = {}
    for item in exam.question_ids or []:
        if isinstance(item, dict):
            result[str(item["id"])] = float(item.get("score", 5.0))
        else:
            result[str(item)] = 5.0
    return result


def _question_to_view(q: Question, scores: dict[str, float]) -> ExamQuestion:
    return ExamQuestion(
        id=q.id,
        question_type=q.question_type.value,
        stem=q.stem,
        options=q.options if q.question_type.value != "short_answer" else None,
        score=scores.get(str(q.id), 5.0),
    )


@router.post("/generate", response_model=ExamGenerateResponse, status_code=202)
async def generate_exam(
    user: CurrentUser,
    payload: ExamGenerateRequest,
) -> ExamGenerateResponse:
    """通过出卷工作流生成一份新试卷（管理员可为任意用户组卷）。"""
    if user["user_id"] != payload.user_id and user["role"] != "admin":
        raise PermissionError_("Cannot generate exam for another user")

    svc = get_exam_gen_service()
    with lf.lf_trace(
        "exam-generate",
        user_id=str(payload.user_id),
        metadata={
            "position": payload.position,
            "num_questions": payload.num_questions,
            "type_counts": payload.type_counts,
        },
    ):
        result = await svc.graph.ainvoke(
            {
                "user_id": payload.user_id,
                "position": payload.position,
                "question_types": payload.question_types,
                "num_questions": payload.num_questions,
                "knowledge_tags": payload.knowledge_tags,
                "type_counts": payload.type_counts,
                "intent_confirmed": True,
            }
        )
    exam_id = result.get("exam_id", 0)
    if not exam_id:
        raise ConflictError("Exam generation failed — no exam_id returned")
    return ExamGenerateResponse(exam_id=exam_id, status="generating")


@router.get("/list", response_model=list[ExamListItem])
async def list_exams(
    user: CurrentUser,
    db: DbSession,
    user_id: int = Query(...),
) -> list[ExamListItem]:
    """列出某用户的试卷，最新在前（管理员传 user_id=-1 列出全部）。"""
    if user["user_id"] != user_id and user["role"] != "admin":
        raise PermissionError_("Cannot list another user's exams")
    stmt = select(Exam).order_by(Exam.created_at.desc())
    if user_id != -1:
        stmt = stmt.where(Exam.user_id == user_id)
    rows = (await db.execute(stmt)).scalars().all()
    return [
        ExamListItem(
            id=e.id,
            position=e.position,
            status=e.status.value,
            total_score=float(e.total_score) if e.total_score else None,
            created_at=e.created_at,
            submitted_at=e.submitted_at,
        )
        for e in rows
    ]


@router.get("/{exam_id}", response_model=ExamDetail)
async def get_exam(
    user: CurrentUser,
    db: DbSession,
    exam_id: int,
) -> ExamDetail:
    """获取试卷详情含题目（不泄露答案）。"""
    exam = await _load_exam(exam_id, user, db)
    scores = _score_map(exam)
    questions = await _load_questions(exam)
    return ExamDetail(
        id=exam.id,
        position=exam.position,
        status=exam.status.value,
        questions=[_question_to_view(q, scores) for q in questions],
        total_score=float(exam.total_score) if exam.total_score else 0.0,
        time_limit=exam.time_limit,
    )


@router.post("/{exam_id}/submit", response_model=ExamSubmitResponse)
async def submit_exam(
    user: CurrentUser,
    db: DbSession,
    exam_id: int,
    payload: ExamSubmitRequest,
) -> ExamSubmitResponse:
    """提交试卷答案 — 通过 Redis 锁 + 数据库唯一约束实现幂等。

    同一试卷二次提交时，返回已有的判分结果，
    而不是重复判分或报错。
    """
    exam = await _load_exam(exam_id, user, db)

    # 已提交过？返回已有的判分结果。
    if exam.status in (ExamStatus.SUBMITTED, ExamStatus.GRADED):
        logger.info("Exam %s already submitted — returning cached result", exam_id)
        return await _build_cached_response(exam_id, db)

    # Redis 锁（SETNX）— 防止并发重复提交。
    qa_svc = get_qa_service()
    redis = qa_svc.working_memory.redis
    lock_key = f"exam:lock:{exam_id}"
    acquired = await redis.set(lock_key, "1", ex=LOCK_TTL, nx=True)
    if not acquired:
        raise ConflictError("Exam is being submitted, please wait")

    try:
        # 写入答案（数据库唯一约束兜底竞态条件）。
        try:
            for ans in payload.answers:
                db.add(
                    ExamAnswer(
                        exam_id=exam_id,
                        question_id=ans.question_id,
                        user_answer=ans.user_answer,
                    )
                )
            exam.status = ExamStatus.SUBMITTED
            exam.submitted_at = datetime.now(timezone.utc)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            # 竞态 — 已被他人写入。返回缓存结果。
            logger.info("IntegrityError on exam %s — returning cached", exam_id)
            return await _build_cached_response(exam_id, db)

        # 运行判卷工作流。
        grade_svc = get_exam_grade_service()
        questions = await _load_questions(exam)
        scores = _score_map(exam)
        with lf.lf_trace(
            "exam-grade",
            user_id=str(exam.user_id),
            metadata={"exam_id": exam_id},
        ):
            grade_result = await grade_svc.graph.ainvoke(
                {
                    "exam_id": exam_id,
                    "user_id": exam.user_id,
                    "questions": [_q_to_dict(q) for q in questions],
                    "answers": [
                        {
                            "question_id": a.question_id,
                            "user_answer": a.user_answer,
                        }
                        for a in payload.answers
                    ],
                    "question_scores": scores,
                }
            )

        # 持久化判分结果。
        await _persist_grades(exam_id, grade_result["graded_answers"], db)
        exam.total_score = Decimal(str(grade_result["total_score"]))
        exam.status = ExamStatus.GRADED
        await db.commit()

        return ExamSubmitResponse(
            exam_id=exam_id,
            status="graded",
            total_score=float(grade_result["total_score"]),
            answers=[
                GradedAnswer(
                    question_id=ga["question_id"],
                    user_answer=ga["user_answer"],
                    score=ga["score"],
                    grading_detail=ga.get("grading_detail"),
                    graded_by=(
                        ga["graded_by"].value
                        if hasattr(ga["graded_by"], "value")
                        else str(ga["graded_by"])
                    ),
                )
                for ga in grade_result["graded_answers"]
            ],
        )
    finally:
        await redis.delete(lock_key)


@router.get("/{exam_id}/result", response_model=ExamResult)
async def get_result(
    user: CurrentUser,
    db: DbSession,
    exam_id: int,
) -> ExamResult:
    """获取考试成绩及逐题分析。"""
    exam = await _load_exam(exam_id, user, db)
    if exam.status != ExamStatus.GRADED:
        raise ConflictError("Exam not yet graded")

    scores = _score_map(exam)
    questions = await _load_questions(exam)

    # 加载已判分的答案。
    stmt = select(ExamAnswer).where(ExamAnswer.exam_id == exam_id)
    answers = (await db.execute(stmt)).scalars().all()

    graded: list[GradedAnswer] = []
    for a in answers:
        graded.append(
            GradedAnswer(
                question_id=a.question_id,
                user_answer=a.user_answer or "",
                score=float(a.score) if a.score else 0.0,
                grading_detail=(
                    a.grading_detail.get("reason", str(a.grading_detail))
                    if isinstance(a.grading_detail, dict)
                    else str(a.grading_detail)
                    if a.grading_detail
                    else None
                ),
                graded_by=a.graded_by.value,
            )
        )

    # 基于知识标签做分析。
    weak, strong = _analyze_result(questions, answers, scores)

    return ExamResult(
        exam=ExamDetail(
            id=exam.id,
            position=exam.position,
            status=exam.status.value,
            questions=[_question_to_view(q, scores) for q in questions],
            total_score=float(exam.total_score) if exam.total_score else 0.0,
            time_limit=exam.time_limit,
        ),
        questions=[_question_to_view(q, scores) for q in questions],
        answers=graded,
        analysis=ExamResultAnalysis(weak_points=weak, strong_points=strong),
    )


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


async def _load_exam(exam_id: int, user: Any, db: Any) -> Exam:
    """加载试卷并校验归属。"""
    exam = await db.get(Exam, exam_id)
    if exam is None:
        raise NotFoundError(f"Exam {exam_id} not found")
    if user and user["user_id"] != exam.user_id:
        raise PermissionError_("Cannot access another user's exam")
    return exam


async def _load_questions(exam: Exam) -> list[Question]:
    """按试卷的题目 ID 加载 Question 行。"""
    from app.core.deps import get_session_factory

    factory = get_session_factory()
    ids = [
        item["id"] if isinstance(item, dict) else item
        for item in (exam.question_ids or [])
    ]
    if not ids:
        return []
    async with factory() as session:
        stmt = select(Question).where(Question.id.in_(ids))
        result = await session.execute(stmt)
        by_id = {q.id: q for q in result.scalars().all()}
    return [by_id[i] for i in ids if i in by_id]


def _q_to_dict(q: Question) -> dict[str, Any]:
    """把 Question ORM 行序列化为普通 dict，供判卷工作流使用。"""
    return {
        "id": q.id,
        "question_type": q.question_type.value,
        "stem": q.stem,
        "options": q.options,
        "answer": q.answer,
        "explanation": q.explanation,
        "knowledge_tags": q.knowledge_tags,
        "difficulty": q.difficulty,
    }


async def _persist_grades(
    exam_id: int, graded: list[dict[str, Any]], db: Any
) -> None:
    """用分数 + 判分详情更新 ExamAnswer 行。"""
    for ga in graded:
        stmt = (
            select(ExamAnswer)
            .where(
                ExamAnswer.exam_id == exam_id,
                ExamAnswer.question_id == ga["question_id"],
            )
        )
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row:
            row.score = Decimal(str(ga["score"]))
            row.grading_detail = {"reason": ga.get("grading_detail", "")}
            row.graded_by = GradedBy.AUTO


async def _build_cached_response(
    exam_id: int, db: Any
) -> ExamSubmitResponse:
    """基于已判分的答案构建提交响应。"""
    stmt = select(ExamAnswer).where(ExamAnswer.exam_id == exam_id)
    answers = (await db.execute(stmt)).scalars().all()
    total = sum(float(a.score or 0) for a in answers)
    return ExamSubmitResponse(
        exam_id=exam_id,
        status="graded",
        total_score=total,
        answers=[
            GradedAnswer(
                question_id=a.question_id,
                user_answer=a.user_answer or "",
                score=float(a.score) if a.score else 0.0,
                grading_detail=(
                    a.grading_detail.get("reason", "")
                    if isinstance(a.grading_detail, dict)
                    else str(a.grading_detail)
                    if a.grading_detail
                    else None
                ),
                graded_by=a.graded_by.value,
            )
            for a in answers
        ],
    )


def _analyze_result(
    questions: list[Question],
    answers: Sequence[ExamAnswer],
    scores: dict[str, float],
) -> tuple[list[str], list[str]]:
    """基于判分结果产出薄弱点 / 掌握点分析。"""
    q_map = {q.id: q for q in questions}
    weak: list[str] = []
    strong: list[str] = []
    for a in answers:
        q = q_map.get(a.question_id)
        if q is None:
            continue
        tags = q.knowledge_tags or []
        max_score = scores.get(str(q.id), 5.0)
        ratio = float(a.score or 0) / max_score if max_score > 0 else 0
        if ratio < 0.6:
            weak.extend(tags)
        elif ratio >= 0.8:
            strong.extend(tags)
    return list(set(weak)), list(set(strong))
