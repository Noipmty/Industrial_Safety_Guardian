# ---------- 阶段 1：构建器 ----------
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# 编译 pymupdf / bcrypt / asyncpg 所需的系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 以加速依赖解析
RUN pip install --no-cache-dir uv

# 预装 CPU 版 torch（容器内 BGE-M3 推理无需 CUDA；先装可避免 uv 从 PyPI 拉取 ~2.5GB 的 CUDA 版）
RUN uv pip install --system torch --index-url https://download.pytorch.org/whl/cpu

COPY pyproject.toml ./
# 仅同步依赖（暂不安装项目本身 —— 保持层缓存稳定）
RUN uv pip compile --output-file=requirements.txt pyproject.toml \
    && uv pip install --system -r requirements.txt

# ---------- 阶段 2：运行时 ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KMP_DUPLICATE_LIB_OK=TRUE

WORKDIR /app

# 运行时系统依赖（bcrypt 需要 libcrypto；libgomp 为 torch 运行时依赖）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libffi8 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制已安装的依赖包
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用源码与初始化脚本
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY gunicorn_conf.py ./
COPY scripts/ ./scripts/
COPY knowledge/ ./knowledge/

# 上传目录（可写；模型目录由 compose 挂载，不打入镜像）
RUN mkdir -p /app/uploads && chmod 755 /app/uploads

EXPOSE 8000

# 健康探针：FastAPI /health 端点
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Gunicorn + Uvicorn worker（worker 数等经 gunicorn_conf.py 读取 GUNICORN_* 环境变量，便于 compose 覆盖）
CMD ["gunicorn", "app.main:app", "-c", "gunicorn.conf.py"]
