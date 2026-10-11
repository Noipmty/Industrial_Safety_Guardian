# ---------- 阶段 1：构建器 ----------
FROM python:3.12-slim AS builder

# 国内网络加固：PyPI 走阿里云内网镜像（http 协议 —— 内网镜像不支持 https，
# 容器内走 https 会报证书主机名不匹配；ECS 公网带宽受限 ~50KB/s，内网 ~1MB/s+，
# 实测差 20 倍。注意：此地址仅在阿里云 ECS 内网可解析，公网构建请改回
# https://mirrors.aliyun.com/pypi/simple）。注意 uv 的索引优先级与 pip 相反：
# --extra-index-url 会先于 --index-url 被检索，因此 torch CPU 源必须作为
# extra index，才能在 torch 解析时先命中 CPU 版（否则会拉到 PyPI 的
# CUDA 版 torch，连带下载 ~2.5GB 的 nvidia-* 依赖）
ARG PYPI_INDEX=http://mirrors.cloud.aliyuncs.com/pypi/simple
ARG TORCH_CPU_INDEX=https://download.pytorch.org/whl/cpu

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 内网镜像走 http，uv 需显式允许非 https 主机（pip 在命令行加 --trusted-host）
ENV UV_ALLOW_INSECURE_HOST=mirrors.cloud.aliyuncs.com

WORKDIR /build

# 编译 pymupdf / bcrypt / asyncpg 所需的系统依赖
# apt 源换成阿里云内网镜像（不吃公网带宽；公网构建请改回 mirrors.aliyun.com）
RUN sed -i "s/deb.debian.org/mirrors.cloud.aliyuncs.com/g" /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 uv 以加速依赖解析（--trusted-host 放行 http 内网源）
RUN pip install --no-cache-dir -i ${PYPI_INDEX} --trusted-host mirrors.cloud.aliyuncs.com uv

COPY pyproject.toml ./
# 仅同步依赖（暂不安装项目本身 —— 保持层缓存稳定）
RUN uv pip compile \
      --index-url ${PYPI_INDEX} \
      --extra-index-url ${TORCH_CPU_INDEX} \
      --output-file=requirements.txt pyproject.toml \
    && uv pip install --system \
      --index-url ${PYPI_INDEX} \
      --extra-index-url ${TORCH_CPU_INDEX} \
      -r requirements.txt

# 生产 WSGI 服务器（独立一层安装，避免改动 pyproject 使 torch 大层缓存失效）
RUN uv pip install --system --no-cache --index-url ${PYPI_INDEX} gunicorn

# ---------- 阶段 2：运行时 ----------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    KMP_DUPLICATE_LIB_OK=TRUE

WORKDIR /app

# 运行时系统依赖（bcrypt 需要 libcrypto；libgomp 为 torch 运行时依赖）
# apt 源换成阿里云内网镜像（不吃公网带宽；公网构建请改回 mirrors.aliyun.com）
RUN sed -i "s/deb.debian.org/mirrors.cloud.aliyuncs.com/g" /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
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
CMD ["gunicorn", "app.main:app", "-c", "gunicorn_conf.py"]
