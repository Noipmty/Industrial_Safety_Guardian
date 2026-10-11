"""chunk 级别的记账表，用于文档幂等同步（P1）。"""

from sqlalchemy import BigInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DocumentChunk(Base):
    """每个已同步的 chunk 对应一行；content_hash 驱动 Milvus 差异比对。"""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("doc_id", "chunk_index", name="uq_doc_chunk_index"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(BigInteger, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
