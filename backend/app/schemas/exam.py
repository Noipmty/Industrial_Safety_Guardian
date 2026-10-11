"""考试相关 DTO —— 与冻结的 ``frontend/openapi.json`` 契约保持一致。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ExamGenerateRequest(BaseModel):
    """POST /api/v1/exam/generate 请求体。"""

    user_id: int = Field(description="用户ID（管理员可为其他用户组卷）")
    position: str = Field(description="岗位（司钻/副司钻/井架工/钻工/泥浆工/安全管理员）")
    question_types: list[str] = Field(description="题型列表 single/multiple/judge/short_answer")
    num_questions: int = Field(ge=1, le=50, description="题目数量")
    knowledge_tags: list[str] | None = Field(default=None, description="知识点过滤标签")
    type_counts: dict[str, int] | None = Field(
        default=None,
        description="各题型精确数量（如 {'single': 9, 'short_answer': 1}），为空时由 LLM 自行分配",
    )


class ExamGenerateResponse(BaseModel):
    """POST /api/v1/exam/generate 响应（202 Accepted）。"""

    exam_id: int = Field(description="生成的试卷ID")
    status: str = Field(default="generating", description="状态")


class ExamQuestion(BaseModel):
    """考试中的一道题（客户端视图 —— 不泄露答案/解析）。"""

    id: int
    question_type: str
    stem: str
    options: list[str] | None = None
    score: float


class ExamDetail(BaseModel):
    """GET /api/v1/exam/{exam_id} 响应。"""

    id: int
    position: str
    status: str
    questions: list[ExamQuestion]
    total_score: float
    time_limit: int


class ExamAnswerItem(BaseModel):
    """提交请求中的一条作答。"""

    question_id: int
    user_answer: str = Field(min_length=1)


class ExamSubmitRequest(BaseModel):
    """POST /api/v1/exam/{exam_id}/submit 请求体。"""

    answers: list[ExamAnswerItem] = Field(min_length=1)


class GradedAnswer(BaseModel):
    """提交响应中的一条判分结果。"""

    question_id: int
    user_answer: str
    score: float
    grading_detail: str | None = None
    graded_by: str


class ExamSubmitResponse(BaseModel):
    """POST /api/v1/exam/{exam_id}/submit 响应。"""

    exam_id: int
    status: str = "graded"
    total_score: float
    answers: list[GradedAnswer]


class ExamResultAnalysis(BaseModel):
    """考试结果的薄弱点/强项分析。"""

    weak_points: list[str]
    strong_points: list[str]


class ExamResult(BaseModel):
    """GET /api/v1/exam/{exam_id}/result 响应。"""

    exam: ExamDetail
    questions: list[ExamQuestion]
    answers: list[GradedAnswer]
    analysis: ExamResultAnalysis


class ExamListItem(BaseModel):
    """GET /api/v1/exam/list 响应中的一行记录。"""

    id: int
    position: str
    status: str
    total_score: float | None = None
    created_at: datetime
    submitted_at: datetime | None = None
