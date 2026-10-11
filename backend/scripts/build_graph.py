"""生产知识图谱全量构建脚本。

从 Milvus ``safety_kb`` collection 拉取全部 chunk 正文，执行
GraphRAG 全量流水线（LLM 三元组抽取 -> 嵌入消歧 -> Neo4j MERGE
写入 -> 社区检测），并把统计写入 Redis 供前端查询。

用法（在 backend/ 目录下执行，gongan 环境）：
    python scripts/build_graph.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 使脚本可直接以 `python scripts/build_graph.py` 运行（将 backend/ 加入导入路径）。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


async def main() -> None:
    from app.services.graph_builder.incremental import full_rebuild
    from app.services.indexing.milvus_store import fetch_all_chunks
    from app.services.llm.client import get_llm_client

    chunks = fetch_all_chunks()
    print(f"从 Milvus 拉取到 {len(chunks)} 个 chunk，开始全量图谱构建…")
    if not chunks:
        print("知识库为空，请先运行 scripts/init_kb.py 入库文档")
        return
    result = await full_rebuild(chunks, llm=get_llm_client())
    print(f"构建完成：{result}")


if __name__ == "__main__":
    asyncio.run(main())
