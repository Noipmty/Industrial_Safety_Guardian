"""FAQ 永久缓存模型 —— 挖掘沉淀的优质问答，命中后跳过完整 RAG 链路。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FaqAnswer(Base):
    """一条沉淀 FAQ：question/answer + BGE-M3 向量（JSON 序列化）。"""

    __tablename__ = "faqs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    question: Mapped[str] = mapped_column(String(512), comment="标准问题")
    answer: Mapped[str] = mapped_column(Text, comment="精校答案")
    embedding: Mapped[str] = mapped_column(
        Text, comment="问题向量（JSON 序列化的 float 列表）"
    )
    source: Mapped[str] = mapped_column(
        String(16), default="manual", comment="来源 manual/mined"
    )
    hit_count: Mapped[int] = mapped_column(
        default=0, comment="累计命中次数"
    )
    enabled: Mapped[bool] = mapped_column(default=True, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
