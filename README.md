# 工安卫士 — 工业安全生产 AI 助手平台

基于 RAG + LLM 工作流的安全生产智能助手，提供知识库问答、智能组卷、智能评卷、知识图谱检索等能力，面向工厂安全培训与考核场景。

## 功能特性

- **安全知识问答**：BGE-M3 混合检索（稠密 + 稀疏词法权重）→ GraphRAG 图谱增强 → qwen-flash 生成，带 4 级缓存（精确 / FAQ / 语义 / RAG）与语义缓存命中
- **智能组卷**：LangGraph 工作流按题型/难度/知识点约束生成试卷，LLM 出题失败自动重试与跨路由降级
- **智能评卷**：客观题自动判分，主观题 LLM 按评分点给分，全链路 Langfuse 可观测
- **知识图谱**：LLM 三元组抽取 → 嵌入消歧 → Neo4j MERGE → 社区检测，支持图谱问答
- **长短期记忆**：Redis 工作记忆（滚动压缩 + 会话终末摘要）+ PostgreSQL/pgvector 长期记忆
- **文档管理**：Markdown/PDF/DOCX 上传解析、分块、向量化、入库进度跟踪
- **可观测性**：Prometheus 指标 + Grafana 仪表盘 + Langfuse 全链路追踪（可选）

## 技术栈

| 层 | 技术 |
|----|------|
| 前端 | Vue 3 + TypeScript + Element Plus + Tailwind CSS + Vite |
| 后端 | Python 3.12 + FastAPI + Gunicorn(UvicornWorker) + LangGraph |
| 嵌入模型 | BGE-M3 本地权重（稠密 1024 维 + 稀疏词法权重） |
| 存储 | MySQL 8（业务）· Redis 7（缓存/记忆）· Milvus 2.4（向量）· Neo4j 5（图谱）· PostgreSQL/pgvector（长期记忆）· MinIO（对象存储） |
| 监控 | Prometheus + Grafana + Langfuse（可选，留空即禁用） |
| LLM | 阿里云百炼 DashScope（qwen-flash 主路由 / qwen-plus 备用路由） |

## 目录结构

```
gongan/
├── backend/
│   ├── app/            # FastAPI 应用（api/services/workflows/tools）
│   ├── alembic/        # 数据库迁移（含种子用户）
│   ├── scripts/        # init_kb.py 知识库初始化 / build_graph.py 图谱构建
│   ├── knowledge/      # 内置安全生产知识库（15 篇 Markdown）
│   └── Dockerfile
├── frontend/
│   ├── src/            # Vue3 单页应用
│   └── Dockerfile      # 多阶段构建（npm build + nginx）
├── infra/
│   ├── docker-compose.yml        # 本地开发编排
│   ├── docker-compose.prod.yml   # 生产部署编排（4核8G 适配）
│   ├── nginx.conf                # 反向代理 + 静态资源
│   └── grafana/                  # 仪表盘预配置
└── eval/               # RAG 评测（RAGAS）
```

## 快速开始（本地开发）

### 1. 启动中间件

```bash
cd infra
docker compose up -d mysql redis etcd minio milvus neo4j postgres
```

### 2. 配置后端环境

```bash
cp .env.example .env   # 填入 LLM_API_KEY（DashScope）等
cd backend
python -m venv .venv && .venv/Scripts/activate   # Windows
pip install -e . -i https://pypi.tuna.tsinghua.edu.cn/simple
# BGE-M3 模型路径经 BGE_M3_PATH 环境变量指定（默认指向本地检出目录）
alembic upgrade head
python scripts/init_kb.py          # 知识库入库 + 检索验证
python scripts/build_graph.py      # 知识图谱构建（需 LLM）
uvicorn app.main:app --port 8000
```

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev    # http://localhost:5174
```

## 生产部署（阿里云 ECS / 4核8G 适配）

```bash
# 1) 下载 BGE-M3 权重（约 2.1GB，ModelScope 国内直连快）
pip3 install modelscope -i https://pypi.tuna.tsinghua.edu.cn/simple
modelscope download --model BAAI/bge-m3 --local_dir models/bge-m3

# 2) 生产环境变量
cp .env.example .env && vi .env
# 必改：ENV=prod / LLM_API_KEY / JWT_SECRET(openssl rand -hex 32) / GUNICORN_WORKERS=1 / BGE_M3_PATH=/models/bge-m3

# 3) 构建并启动全部服务
cd infra
docker compose -f docker-compose.prod.yml up -d --build

# 4) 初始化数据
docker exec gongan-backend alembic upgrade head
docker exec gongan-backend python scripts/init_kb.py
docker exec gongan-backend python scripts/build_graph.py

# 5) 验证
curl http://127.0.0.1/health
```

> 安全组仅需放行 22/80；MySQL、Redis、Milvus 等中间件端口均绑定 127.0.0.1，不对公网暴露。

## 演示账号

| 角色 | 账号 | 密码 | 说明 |
|------|------|------|------|
| 管理员 | `admin` | `admin123` | 文档管理 / FAQ 管理 / 用户管理 |
| 工人 | `worker` | `worker123` | 问答 / 考试 |

Grafana：`admin / gongan2024`（生产环境经 SSH 隧道访问 `127.0.0.1:3000`）。

## 配置说明

所有敏感配置集中在根目录 `.env`（已被 `.gitignore` 排除，不入库）：

| 变量 | 说明 |
|------|------|
| `LLM_API_KEY` / `LLM_BASE_URL` | 主路由 LLM（默认阿里云百炼） |
| `LLM_FALLBACK_*` | 备用路由（主路由故障自动切换） |
| `JWT_SECRET` | 登录态签名密钥，生产必换 |
| `BGE_M3_PATH` | BGE-M3 本地权重路径 |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | 留空则禁用追踪 |

## License

仅供学习交流使用。
