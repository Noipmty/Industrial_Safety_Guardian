"""BGE-M3 embedding 服务（本地权重，稠密 + 稀疏）。

模型在首次使用时才惰性加载，避免 import 模块就触发数秒的
torch 启动。稀疏向量是 BGE-M3 产出的词法权重
（token-id -> weight），用于填充 Milvus 的 sparse 字段以支持
混合检索。

关于 BM25 的说明：提示词中的 "BM25 Function" 指 Milvus 2.5 的
服务端 Function API；当前部署的 Milvus 2.4.10 不支持该特性，
因此改用 BGE-M3 词法权重填充 sparse 字段（能力等价：
用学习到的词权重替代原始 TF-IDF 打分）。
"""

from __future__ import annotations

import threading
from typing import Any

from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """BGEM3FlagModel 的惰性单例封装。"""

    _lock = threading.Lock()

    def __init__(self) -> None:
        self._model: Any = None

    def _ensure_model(self) -> Any:
        with EmbeddingService._lock:
            if self._model is None:
                from FlagEmbedding import BGEM3FlagModel  # 重量级导入，惰性执行

                path = get_settings().embedding.bge_m3_path
                logger.info("Loading BGE-M3 from %s", path)
                self._model = BGEM3FlagModel(path, use_fp16=False)
        return self._model

    def encode(
        self, texts: list[str], batch_size: int = 8
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """返回给定文本的 (稠密向量列表, 稀疏字典列表)。"""
        model = self._ensure_model()
        output = model.encode(
            texts,
            batch_size=batch_size,
            max_length=1024,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense = output["dense_vecs"].tolist()
        sparse: list[dict[int, float]] = []
        for weights in output["lexical_weights"]:
            sparse.append({int(token): float(weight) for token, weight in weights.items()})
        return dense, sparse

    def encode_dense(self, texts: list[str]) -> list[list[float]]:
        """仅稠密编码的便捷方法（测试 / 记忆层使用）。"""
        dense, _ = self.encode(texts)
        return dense


class DenseOnlyAdapter:
    """将 EmbeddingService 适配为记忆层与语义缓存使用的仅稠密
    ``encode`` 接口（不携带稀疏负载的开销）。"""

    def __init__(self, service: EmbeddingService) -> None:
        self._service = service

    def encode(self, texts: list[str]) -> list[list[float]]:
        """仅稠密编码（记忆层协议）。"""
        return self._service.encode_dense(texts)

    def encode_dense(self, texts: list[str]) -> list[list[float]]:
        return self._service.encode_dense(texts)


_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    """返回共享的 embedding 服务单例。"""
    global _service
    if _service is None:
        _service = EmbeddingService()
    return _service


_adapter: DenseOnlyAdapter | None = None


def get_dense_embedder() -> DenseOnlyAdapter:
    """记忆层 / 缓存层共享的仅稠密 embedder 适配器。"""
    global _adapter
    if _adapter is None:
        _adapter = DenseOnlyAdapter(get_embedding_service())
    return _adapter
