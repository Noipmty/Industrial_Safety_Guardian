"""ORM 模型包 —— 导入所有模型，确保 Base.metadata 完整填充。"""

from app.models.audit_log import AuditLog
from app.models.base import Base, TimestampMixin
from app.models.chunk import DocumentChunk
from app.models.document import DocStatus, DocType, KnowledgeDocument, Session
from app.models.exam import (
    Exam,
    ExamAnswer,
    ExamStatus,
    GradedBy,
    Question,
    QuestionType,
)
from app.models.user import Position, Role, User

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "Position",
    "Role",
    "KnowledgeDocument",
    "DocType",
    "DocStatus",
    "Session",
    "DocumentChunk",
    "Question",
    "QuestionType",
    "Exam",
    "ExamStatus",
    "ExamAnswer",
    "GradedBy",
    "AuditLog",
]
