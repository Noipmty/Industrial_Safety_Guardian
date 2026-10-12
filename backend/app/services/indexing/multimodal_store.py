"""页面级多模态（视觉）检索的 Milvus collection。

collection ``safety_visual`` 的 schema：
    - dense   FLOAT_VECTOR(1024)  BGE-M3 / ColQwen2 pooled，HNSW + COSINE
    - sparse  SPARSE_FLOAT_VECTOR  词法权重（MaxSim 代理），倒排索引 + IP
    - 元数据：page_id / doc_id / page_num / page_hash / description / image_path / version

两阶段检索与编码器设计保持一致：
    阶段 1：稠密 ANN 检索（pooling 预筛）
    阶段 2：稀疏 MaxSim 重排
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.config import get_settings
from app.core.logger import get_logger

logger = get_logger(__name__)

VISUAL_COLLECTION = "safety_visual"


@dataclass(slots=True)
class PageRecord:
    """一条待插入视觉 collection 的页面记录。"""

    page_id: str  # "{doc_id}:{page_num}"
    doc_id: int
    page_num: int
    page_hash: str
    description: str
    image_path: str
    version: str
    dense: list[float]
    sparse: dict[int, float]


def _connect() -> None:
    if not connections.has_connection("default"):
        settings = get_settings()
        connections.connect(alias="default", uri=settings.milvus.uri)


def _visual_schema() -> CollectionSchema:
    fields = [
        FieldSchema("pk", DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema("page_id", DataType.VARCHAR, max_length=64),
        FieldSchema("doc_id", DataType.INT64),
        FieldSchema("page_num", DataType.INT64),
        FieldSchema("page_hash", DataType.VARCHAR, max_length=64),
        FieldSchema("description", DataType.VARCHAR, max_length=2048),
        FieldSchema("image_path", DataType.VARCHAR, max_length=512),
        FieldSchema("version", DataType.VARCHAR, max_length=32),
        FieldSchema("dense", DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema("sparse", DataType.SPARSE_FLOAT_VECTOR),
    ]
    return CollectionSchema(
        fields, description="工安卫士 page-level visual collection"
    )


def ensure_visual_collection() -> Collection:
    """视觉 collection + 索引缺失时创建；返回已加载的 collection。"""
    _connect()
    if utility.has_collection(VISUAL_COLLECTION):
        collection = Collection(VISUAL_COLLECTION)
    else:
        collection = Collection(VISUAL_COLLECTION, _visual_schema())
        collection.create_index(
            "dense",
            {
                "index_type": "HNSW",
                "metric_type": "COSINE",
                "params": {"M": 16, "efConstruction": 256},
            },
        )
        collection.create_index(
            "sparse",
            {
                "index_type": "SPARSE_INVERTED_INDEX",
                "metric_type": "IP",
                "params": {"drop_ratio_build": 0.2},
            },
        )
        logger.info("Created visual collection %s", VISUAL_COLLECTION)
    if (
        not utility.load_state(VISUAL_COLLECTION)
        or str(utility.load_state(VISUAL_COLLECTION)) != "Loaded"
    ):
        collection.load()
    return collection


def insert_pages(collection: Collection, records: list[PageRecord]) -> int:
    """插入页面记录；返回插入条数。"""
    if not records:
        return 0
    data: list[list[Any]] = [
        [r.page_id for r in records],
        [r.doc_id for r in records],
        [r.page_num for r in records],
        [r.page_hash for r in records],
        [r.description for r in records],
        [r.image_path for r in records],
        [r.version for r in records],
        [r.dense for r in records],
        [
            {str(token): weight for token, weight in r.sparse.items()}
            for r in records
        ],
    ]
    collection.insert(data)
    collection.flush()
    return len(records)


def delete_visual_by_doc(collection: Collection, doc_id: int) -> None:
    """删除属于某文档的全部页面（幂等删除）。"""
    collection.delete(f"doc_id == {doc_id}")
    collection.flush()


def has_page_hash(collection: Collection, page_hash: str) -> bool:
    """检查给定内容 hash 的页面是否已存在。"""
    results = collection.query(
        expr=f'page_hash == "{page_hash}"',
        output_fields=["page_id"],
        limit=1,
    )
    return len(results) > 0


def visual_search(
    collection: Collection,
    query_dense: list[float],
    query_sparse: dict[int, float],
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """两阶段视觉检索：稠密 ANN → 稀疏 MaxSim 重排。

    阶段 1：稠密 ANN 检索，取 2× top_k 个候选。
    阶段 2：按稀疏 IP（MaxSim 代理）重新打分，返回 top_k。
    """
    from pymilvus import AnnSearchRequest, WeightedRanker

    dense_req = AnnSearchRequest(
        data=[query_dense],
        anns_field="dense",
        param={"metric_type": "COSINE", "params": {"ef": 128}},
        limit=top_k * 3,  # 超量召回，供重排使用
        expr=None,
    )
    sparse_data = [{str(token): weight for token, weight in query_sparse.items()}]
    sparse_req = AnnSearchRequest(
        data=sparse_data,
        anns_field="sparse",
        param={"metric_type": "IP", "params": {}},
        limit=top_k * 3,
        expr=None,
    )
    results = collection.hybrid_search(
        reqs=[dense_req, sparse_req],
        rerank=WeightedRanker(0.6, 0.4),  # 稠密 pooling + 稀疏 MaxSim
        limit=top_k,
        output_fields=[
            "page_id", "doc_id", "page_num", "page_hash",
            "description", "image_path", "version",
        ],
    )
    hits: list[dict[str, Any]] = []
    for hit in results[0]:
        entity = hit.entity
        hits.append(
            {
                "id": hit.id,
                "score": hit.distance,
                "page_id": entity.get("page_id"),
                "doc_id": entity.get("doc_id"),
                "page_num": entity.get("page_num"),
                "page_hash": entity.get("page_hash"),
                "description": entity.get("description"),
                "image_path": entity.get("image_path"),
                "version": entity.get("version"),
            }
        )
    return hits
