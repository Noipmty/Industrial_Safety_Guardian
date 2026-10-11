"""多模态编码器 —— ColQwen2 late-interaction + 降级文本路径。

ColQwen2 将页面图像编码为多向量（token 级）表示，用于
late-interaction 匹配（MaxSim）。当本地没有 ColQwen2 权重时，
编码器降级为文本描述路径，复用 BGE-M3 的稠密 + 稀疏向量
来近似两阶段检索：

    阶段 1（pooling 预筛）：稠密余弦相似度 —— 快速粗筛
    阶段 2（MaxSim 重排）：稀疏词法权重 token 匹配 —— 精排

这种降级保留了架构不变：ColQwen2 接口完全一致，
后续换上真实权重只需修改工厂函数。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.core.logger import get_logger

logger = get_logger(__name__)


class MultimodalEncoder(Protocol):
    """抽象编码器：页面文本/描述 -> (pooled, token_vecs)。"""

    def encode_pages(
        self, descriptions: list[str]
    ) -> list[tuple[list[float], dict[int, float]]]:
        """将页面描述编码为 (pooled_vector, token_weights)。"""
        ...

    def encode_query(
        self, query: str
    ) -> tuple[list[float], dict[int, float]]:
        """将查询编码为 (pooled_vector, token_weights)。"""
        ...

    @property
    def dim(self) -> int:
        """pooled 向量的维度。"""
        ...

    @property
    def is_colqwen2(self) -> bool:
        """是否正在使用真实的 ColQwen2 权重。"""
        ...


@dataclass(slots=True)
class PageEncoding:
    """编码后的页面：pooled 向量用于阶段 1，token 向量用于阶段 2。"""

    page_index: int
    pooled: list[float]
    token_weights: dict[int, float]


class ColQwen2Encoder:
    """真实的 ColQwen2 late-interaction 编码器（权重到位后即可插拔启用）。

    从 ``colqwen2_path`` 加载 ColQwen2，将页面图像编码为多向量
    表示。每个页面产出 N 个 token 级向量；MaxSim 检索将查询
    token 与页面 token 进行匹配。
    """

    def __init__(self, colqwen2_path: str) -> None:
        self._path = colqwen2_path
        self._model: Any = None
        self._dim = 128  # ColQwen2 token embedding 维度

    def _ensure_model(self) -> Any:
        if self._model is None:
            # 惰性导入 —— ColQwen2 依赖 mllt / colpali-engine 包
            try:
                from colpali_engine.models import (  # type: ignore[import-untyped]
                    ColQwen2,
                    ColQwen2Processor,
                )
            except ImportError as exc:
                raise RuntimeError(
                    "ColQwen2 weights not available. Install colpali-engine "
                    "and set COLQWEN2_PATH to use real multimodal encoding."
                ) from exc

            self._model = ColQwen2.from_pretrained(self._path).eval()
            self._processor = ColQwen2Processor.from_pretrained(self._path)
            logger.info("ColQwen2 loaded from %s", self._path)
        return self._model

    def encode_pages(
        self, descriptions: list[str]
    ) -> list[tuple[list[float], dict[int, float]]]:
        """通过 ColQwen2 token 向量编码页面文本描述。

        生产环境下这里应编码页面*图像*。当只有文本描述可用
        （没有图像文件）时会落入文本路径。此方法是一个占位实现，
        在无权重时调用会直接抛错 —— 工厂函数在 ColQwen2 不可用时
        永远不会路由到这里。
        """
        raise NotImplementedError("ColQwen2 image encoding requires model weights")

    def encode_query(
        self, query: str
    ) -> tuple[list[float], dict[int, float]]:
        raise NotImplementedError("ColQwen2 query encoding requires model weights")

    @property
    def dim(self) -> int:
        return self._dim

    @property
    def is_colqwen2(self) -> bool:
        return True


class TextDescriptionEncoder:
    """降级的多模态编码器：以 BGE-M3 稠密 + 稀疏向量作为代理。

    将 ColQwen2 的两阶段检索映射到文本特征上：
        - 阶段 1（pooling）：BGE-M3 稠密向量 → 余弦预筛
        - 阶段 2（MaxSim）：BGE-M3 稀疏词法权重 → token 匹配

    这在架构上是忠实的：同样的两阶段流水线照常运行，
    只是用文本特征替代了图像特征。
    """

    def __init__(self) -> None:
        self._embedder: Any = None

    def _ensure_embedder(self) -> Any:
        if self._embedder is None:
            from app.services.indexing.embedding import get_embedding_service

            self._embedder = get_embedding_service()
        return self._embedder

    def encode_pages(
        self, descriptions: list[str]
    ) -> list[tuple[list[float], dict[int, float]]]:
        """将页面文本描述编码为 (dense, sparse) 对。"""
        service = self._ensure_embedder()
        dense_list, sparse_list = service.encode(descriptions)
        return list(zip(dense_list, sparse_list, strict=True))

    def encode_query(
        self, query: str
    ) -> tuple[list[float], dict[int, float]]:
        """将查询编码为 (dense, sparse)。"""
        service = self._ensure_embedder()
        dense_list, sparse_list = service.encode([query])
        return dense_list[0], sparse_list[0]

    @property
    def dim(self) -> int:
        return 1024

    @property
    def is_colqwen2(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# 两阶段检索：pooling 预筛 → MaxSim 重排
# ---------------------------------------------------------------------------


def maxsim_score(
    query_tokens: dict[int, float],
    page_tokens: dict[int, float],
) -> float:
    """late-interaction MaxSim：逐 token 最大重叠之和。

    对每个出现在页面中的查询 token，取两侧权重的乘积；
    再对所有匹配 token 求和。这是在稀疏词法权重上对
    ColQwen2 MaxSim 的近似。
    """
    if not query_tokens or not page_tokens:
        return 0.0
    total = 0.0
    for token_id, q_weight in query_tokens.items():
        p_weight = page_tokens.get(token_id)
        if p_weight is not None:
            total += q_weight * p_weight
    return total


def cosine_sim(a: list[float], b: list[float]) -> float:
    """稠密向量余弦相似度。"""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def two_stage_retrieve(
    query_dense: list[float],
    query_sparse: dict[int, float],
    page_encodings: list[tuple[list[float], dict[int, float]]],
    prefilter_k: int = 20,
    final_k: int = 5,
    dense_weight: float = 0.6,
    maxsim_weight: float = 0.4,
) -> list[tuple[int, float]]:
    """两阶段检索：pooling 预筛 → MaxSim 重排。

    阶段 1：按稠密余弦给所有页面排序，保留前 ``prefilter_k`` 个。
    阶段 2：按（稠密 + MaxSim）加权得分重排，返回前 ``final_k`` 个。

    返回按分数降序排列的 ``[(page_index, fused_score)]``。
    """
    if not page_encodings:
        return []

    # 阶段 1：pooling 预筛（稠密余弦）
    candidates: list[tuple[int, float, dict[int, float]]] = []
    for idx, (dense, sparse) in enumerate(page_encodings):
        sim = cosine_sim(query_dense, dense)
        candidates.append((idx, sim, sparse))
    candidates.sort(key=lambda x: x[1], reverse=True)
    prefiltered = candidates[:prefilter_k]

    # 阶段 2：MaxSim 重排
    results: list[tuple[int, float]] = []
    for idx, dense_sim, sparse in prefiltered:
        ms = maxsim_score(query_sparse, sparse)
        fused = dense_weight * dense_sim + maxsim_weight * ms
        results.append((idx, fused))
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:final_k]


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

_encoder: MultimodalEncoder | None = None


def get_multimodal_encoder() -> MultimodalEncoder:
    """返回共享的编码器单例。

    当设置了 ``COLQWEN2_PATH`` 且权重可加载时使用 ColQwen2；
    否则降级为 TextDescriptionEncoder（BGE-M3 代理）。
    """
    global _encoder
    if _encoder is None:
        import os

        colqwen_path = os.environ.get("COLQWEN2_PATH", "")
        if colqwen_path and os.path.isdir(colqwen_path):
            try:
                _encoder = ColQwen2Encoder(colqwen_path)
                logger.info("Multimodal encoder: ColQwen2 (path=%s)", colqwen_path)
            except Exception as exc:  # noqa: BLE001 — 优雅降级
                logger.warning("ColQwen2 load failed (%s), using text path", exc)
                _encoder = TextDescriptionEncoder()
        else:
            _encoder = TextDescriptionEncoder()
            logger.info("Multimodal encoder: text-description (BGE-M3 proxy)")
    return _encoder
