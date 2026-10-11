"""安全知识库的 Milvus collection 管理。

collection ``safety_kb`` 的 schema：
    - dense  FLOAT_VECTOR(1024)   BGE-M3 稠密向量，HNSW + COSINE
    - sparse SPARSE_FLOAT_VECTOR  BGE-M3 词法权重，倒排索引 + IP
    - 元数据：doc_id / chunk_index / text / doc_type / position / version
    - content_hash 用于幂等重同步
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


@dataclass(slots=True)
class ChunkRecord:
    """一条待插入 Milvus 的 chunk 记录。"""

    chunk_id: str  # "{doc_id}:{chunk_index}"
    doc_id: int
    chunk_index: int
    text: str
    content_hash: str
    doc_type: str
    position: str
    version: str
    dense: list[float]
    sparse: dict[int, float]


def connect_milvus() -> None:
    """将共享别名连接到配置的 Milvus 实例。"""
    if not connections.has_connection("default"):
        settings = get_settings()
        connections.connect(alias="default", uri=settings.milvus.uri)


def _schema() -> CollectionSchema:
    fields = [
        FieldSchema("pk", DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema("chunk_id", DataType.VARCHAR, max_length=64),
        FieldSchema("doc_id", DataType.INT64),
        FieldSchema("chunk_index", DataType.INT64),
        FieldSchema("text", DataType.VARCHAR, max_length=8192),
        FieldSchema("content_hash", DataType.VARCHAR, max_length=64),
        FieldSchema("doc_type", DataType.VARCHAR, max_length=64),
        FieldSchema("position", DataType.VARCHAR, max_length=64),
        FieldSchema("version", DataType.VARCHAR, max_length=32),
        FieldSchema("dense", DataType.FLOAT_VECTOR, dim=1024),
        FieldSchema("sparse", DataType.SPARSE_FLOAT_VECTOR),
    ]
    schema = CollectionSchema(fields, description="工安卫士 safety knowledge base")
    return schema


def ensure_collection() -> Collection:
    """collection + 索引缺失时创建；返回已加载的 collection。"""
    connect_milvus()
    name = get_settings().milvus.collection
    if utility.has_collection(name):
        collection = Collection(name)
    else:
        collection = Collection(name, _schema())
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
        logger.info("Created Milvus collection %s with dense+sparse indexes", name)
    if not utility.load_state(name) or str(utility.load_state(name)) != "Loaded":
        collection.load()
    return collection


def fetch_all_chunks(limit: int = 16384) -> list[dict[str, Any]]:
    """拉取 collection 内全部 chunk 正文（供图谱构建使用）。

    返回 ``[{"chunk_id", "doc_id", "text"}]``，按 chunk_id 升序。
    """
    collection = ensure_collection()
    rows = collection.query(
        expr="doc_id >= 0",
        output_fields=["chunk_id", "doc_id", "text"],
        limit=limit,
    )
    return [
        {
            "chunk_id": str(r["chunk_id"]),
            "doc_id": int(r["doc_id"]),
            "text": str(r["text"]),
        }
        for r in rows
    ]


def insert_chunks(collection: Collection, records: list[ChunkRecord]) -> int:
    """插入 chunk 记录；返回插入条数。"""
    if not records:
        return 0
    data: list[list[Any]] = [
        [r.chunk_id for r in records],
        [r.doc_id for r in records],
        [r.chunk_index for r in records],
        [r.text for r in records],
        [r.content_hash for r in records],
        [r.doc_type for r in records],
        [r.position for r in records],
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


def delete_by_doc(collection: Collection, doc_id: int) -> None:
    """删除属于某文档的全部 chunk（幂等删除）。"""
    collection.delete(f"doc_id == {doc_id}")
    collection.flush()


def hybrid_search(
    collection: Collection,
    query_dense: list[float],
    query_sparse: dict[int, float],
    top_k: int = 10,
    doc_types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """执行一次混合（稠密 + 稀疏）检索，返回合并后的候选。

    加权 ranker 给稠密语义 0.7、词法匹配 0.3 的权重，符合
    安全问答场景：同义改写比关键词命中更重要。
    """
    from pymilvus import AnnSearchRequest, WeightedRanker

    dense_req = AnnSearchRequest(
        data=[query_dense],
        anns_field="dense",
        param={"metric_type": "COSINE", "params": {"ef": 128}},
        limit=top_k,
    )
    sparse_data = [{str(token): weight for token, weight in query_sparse.items()}]
    sparse_req = AnnSearchRequest(
        data=sparse_data,
        anns_field="sparse",
        param={"metric_type": "IP", "params": {}},
        limit=top_k,
    )
    expr = None
    if doc_types:
        quoted = ", ".join(f'"{t}"' for t in doc_types)
        expr = f"doc_type in [{quoted}]"
        dense_req.expr = expr
        sparse_req.expr = expr

    results = collection.hybrid_search(
        reqs=[dense_req, sparse_req],
        rerank=WeightedRanker(0.7, 0.3),
        limit=top_k,
        output_fields=[
            "chunk_id", "doc_id", "chunk_index", "text", "doc_type", "position", "version",
        ],
    )
    hits: list[dict[str, Any]] = []
    for hit in results[0]:
        entity = hit.entity
        hits.append(
            {
                "id": hit.id,
                "score": hit.distance,
                "chunk_id": entity.get("chunk_id"),
                "doc_id": entity.get("doc_id"),
                "chunk_index": entity.get("chunk_index"),
                "text": entity.get("text"),
                "doc_type": entity.get("doc_type"),
                "position": entity.get("position"),
                "version": entity.get("version"),
            }
        )
    return hits
