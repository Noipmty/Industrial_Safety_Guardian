"""题目、考试与考试作答模型。"""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import Mapped, mapped_column

from app.core.compat import StrEnum
from app.models.base import Base


class QuestionType(StrEnum):
    """题型。"""

    SINGLE = "single"
    MULTIPLE = "multiple"
    JUDGE = "judge"
    SHORT_ANSWER = "short_answer"


class ExamStatus(StrEnum):
    """考试生命周期状态。"""

    CREATED = "created"
    SUBMITTED = "submitted"
    GRADED = "graded"


class GradedBy(StrEnum):
    """判卷方。"""

    AUTO = "auto"
    MANUAL = "manual"


class Question(Base):
    """单道题目，可选关联来源文档。"""

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    doc_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("documents.id"),
        nullable=True,
    )
    question_type: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type_enum", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    stem: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    options: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    answer: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    knowledge_tags: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    position_tags: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    difficulty: Mapped[int] = mapped_column(
        TINYINT,
        server_default=text("1"),
        nullable=False,
    )
    source_chunk_id: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    verified: Mapped[bool] = mapped_column(
        Boolean,
        server_default=text("0"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )


class Exam(Base):
    """分配给某用户的考试，包含一组题目。"""

    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    position: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    question_ids: Mapped[list | None] = mapped_column(
        JSON,
        nullable=True,
    )
    status: Mapped[ExamStatus] = mapped_column(
        Enum(ExamStatus, name="exam_status_enum", values_callable=lambda e: [m.value for m in e]),
        server_default="created",
        nullable=False,
    )
    total_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    time_limit: Mapped[int] = mapped_column(
        BigInteger,
        server_default=text("3600"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        nullable=False,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )


class ExamAnswer(Base):
    """用户在一次考试中对某道题的作答。"""

    __tablename__ = "exam_answers"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question"),
    )

    id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    exam_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("exams.id"),
        nullable=False,
    )
    question_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("questions.id"),
        nullable=False,
    )
    user_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    grading_detail: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
    )
    graded_by: Mapped[GradedBy] = mapped_column(
        Enum(GradedBy, name="exam_answer_graded_by", values_callable=lambda e: [m.value for m in e]),
        server_default="auto",
        nullable=False,
    )
