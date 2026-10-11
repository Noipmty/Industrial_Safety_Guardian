# 工安卫士 运维手册（Runbook）

> P0 阶段框架，后续按实际故障补充完善。

## 目录

1. [LLM 超时](#1-llm-超时)
2. [Milvus 挂](#2-milvus-挂)
3. [Neo4j 挂](#3-neo4j-挂)
4. [Redis 满](#4-redis-满)
5. [向量模型异常](#5-向量模型异常)

---

## 1. LLM 超时

### 症状
- 用户问答请求长时间无响应，接口返回 504 Gateway Timeout。
- 日志中出现 `LLM request timed out` 或 `asyncio.TimeoutError`。

### 排查命令
```bash
# 查看后端日志中的超时记录
docker logs gongan-backend 2>&1 | grep -i "timeout"

# 测试 LLM API 连通性
curl -w "\n%{time_total}s\n" -o /dev/null -s -X POST $LLM_BASE_URL/chat/completions \
  -H "Authorization: Bearer $LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"ping"}]}'

# 检查 API Key 余额/配额
curl -s $LLM_BASE_URL/usage -H "Authorization: Bearer $LLM_API_KEY"
```

### 处理步骤
1. 确认 LLM 服务商是否正常（查看服务商状态页）。
2. 若 API Key 失效或配额用尽，更换为备用 Key 或切换 `LLM_FALLBACK_MODEL`。
3. 若网络不通，检查出口网络和代理配置。
4. 临时降低并发或增大请求超时参数。

### 恢复验证
```bash
# 发送测试请求确认响应正常
curl -s -X POST $LLM_BASE_URL/chat/completions \
  -H "Authorization: Bearer $LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"你好"}]}' | jq .choices[0].message.content
```

---

## 2. Milvus 挂

### 症状
- 向量检索接口报错，返回 500。
- 日志中出现 `MilvusException` 或连接 `localhost:19530` 失败。
- RAG 问答无法召回知识。

### 排查命令
```bash
# 检查 Milvus 容器状态
docker ps | grep gongan-milvus

# 查看健康端点
curl -s http://localhost:9091/healthz

# 查看 Milvus 日志
docker logs gongan-milvus --tail 100

# 检查依赖（etcd + minio）状态
docker ps | grep -E "gongan-etcd|gongan-minio"
```

### 处理步骤
1. 若容器未运行：`cd infra && docker compose up -d milvus`。
2. 若依赖（etcd/minio）异常，先恢复依赖再重启 Milvus。
3. 若数据损坏，从最近备份恢复 etcd 和 minio 卷。
4. 若磁盘满，清理 minio 过期对象后重启。

### 恢复验证
```bash
# 健康端点返回 OK
curl -s http://localhost:9091/healthz

# 列出 collections 确认数据正常
python -c "
from pymilvus import connections, utility
connections.connect(uri='http://localhost:19530')
print(utility.list_collections())
"
```

---

## 3. Neo4j 挂

### 症状
- 知识图谱查询接口报错，返回 500。
- 日志中出现 `ServiceUnavailable` 或连接 `bolt://localhost:7687` 失败。
- 图谱构建任务中断。

### 排查命令
```bash
# 检查 Neo4j 容器状态
docker ps | grep gongan-neo4j

# 测试 Bolt 端口连通性
curl -s http://localhost:7474

# 查看 Neo4j 日志
docker logs gongan-neo4j --tail 100

# 检查认证是否正常
docker exec gongan-neo4j cypher-shell -u neo4j -p gongan2024 "RETURN 1"
```

### 处理步骤
1. 若容器未运行：`cd infra && docker compose up -d neo4j`。
2. 若认证失败（密码错误），检查 `NEO4J_PASSWORD` 环境变量是否与容器配置一致。
3. 若数据损坏，从 `neo4j_data` 卷备份恢复。
4. 若内存不足，调大容器内存限制后重启。

### 恢复验证
```bash
# Cypher 查询正常返回
docker exec gongan-neo4j cypher-shell -u neo4j -p gongan2024 "MATCH (n) RETURN count(n) AS node_count"

# 后端图谱查询接口正常
curl -s http://localhost:8000/api/v1/graph/nodes?limit=1
```

---

## 4. Redis 满

### 症状
- 缓存写入失败，日志出现 `OOM command not allowed`。
- 会话/限流功能异常。
- 接口响应变慢。

### 排查命令
```bash
# 查看内存使用情况
docker exec gongan-redis redis-cli INFO memory | grep -E "used_memory_human|maxmemory_human|maxmemory_policy"

# 查看各 db key 数量
docker exec gongan-redis redis-cli INFO keyspace

# 查看大 key
docker exec gongan-redis redis-cli --bigkeys

# 查看过期策略
docker exec gongan-redis redis-cli CONFIG GET maxmemory-policy
```

### 处理步骤
1. 识别并清理无用大 key：`docker exec gongan-redis redis-cli DEL <key>`。
2. 若为临时数据膨胀，手动执行 `FLUSHDB`（仅限非持久化缓存 db）。
3. 调整 `maxmemory` 和淘汰策略（建议 `allkeys-lru`）。
4. 重启 Redis：`cd infra && docker compose restart redis`。

### 恢复验证
```bash
# 内存使用率正常
docker exec gongan-redis redis-cli INFO memory | grep used_memory_human

# 读写测试
docker exec gongan-redis redis-cli SET healthcheck "ok" EX 60
docker exec gongan-redis redis-cli GET healthcheck
```

---

## 5. 向量模型异常

### 症状
- 文档索引任务失败，向量入库报错。
- 问答检索召回为空或语义不相关。
- 日志中出现 embedding 维度不匹配或模型加载失败。

### 排查命令
```bash
# 查看后端日志中的 embedding 错误
docker logs gongan-backend 2>&1 | grep -iE "embedding|vector|dimension"

# 测试向量模型服务连通性
curl -s -X POST http://localhost:8000/api/v1/health/embedding | jq .

# 检查 Milvus collection 维度
python -c "
from pymilvus import connections, Collection
connections.connect(uri='http://localhost:19530')
c = Collection('gongan_docs')
print('dim:', c.schema.fields)
print('count:', c.num_entities)
"

# 查看向量模型服务进程
docker ps | grep -i embedding
```

### 处理步骤
1. 确认向量模型服务是否存活，若挂掉则重启模型服务容器。
2. 若维度不匹配，检查 embedding 模型版本是否变更，必要时重建 collection。
3. 若 GPU 内存不足，清理显存后重启模型服务。
4. 若为模型权重损坏，从备份重新拉取权重文件。

### 恢复验证
```bash
# 健康检查接口正常
curl -s http://localhost:8000/api/v1/health/embedding | jq .status

# 向量入库测试
curl -s -X POST http://localhost:8000/api/v1/index/test \
  -H "Content-Type: application/json" \
  -d '{"text":"工安卫士测试文本"}' | jq .

# 检索召回正常
curl -s -X POST http://localhost:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{"query":"安全生产注意事项","top_k":3}' | jq .results[0].content
```
