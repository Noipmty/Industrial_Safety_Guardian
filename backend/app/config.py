"""分层应用配置（dev / staging / prod）。

所有密钥均从环境变量读取。本地 ML 模型权重（BGE-M3 / BGE-reranker /
query classifier）复用已有的 edu_agent_project 检出目录，无需重新下载。
"""

from functools import lru_cache
from typing import Annotated

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _split_origins(value: object) -> object:
    """允许 CORS_ORIGINS 为 JSON 列表或逗号分隔字符串。"""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class _EnvBase(BaseSettings):
    """公共配置基类：统一从项目 .env 文件与环境变量读取。

    所有嵌套子配置必须继承本类，否则 ``default_factory`` 实例化时
    读不到 .env 文件（只会读进程环境变量）。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


class MysqlSettings(_EnvBase):
    """MySQL（业务数据）连接配置。"""

    url: str = Field(
        default="mysql+aiomysql://root:gongan2024@localhost:3306/gongan_weishi",
        alias="MYSQL_URL",
    )


class RedisSettings(_EnvBase):
    """Redis（缓存 / 队列 / 工作记忆）配置。"""

    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")


class MilvusSettings(_EnvBase):
    """Milvus 向量数据库配置。"""

    uri: str = Field(default="http://localhost:19530", alias="MILVUS_URI")
    collection: str = Field(default="safety_kb", alias="MILVUS_COLLECTION")


class Neo4jSettings(_EnvBase):
    """Neo4j 图数据库配置。"""

    uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    user: str = Field(default="neo4j", alias="NEO4J_USER")
    password: str = Field(default="gongan2024", alias="NEO4J_PASSWORD")


class PostgresSettings(_EnvBase):
    """PostgreSQL + pgvector（记忆层）配置。"""

    url: str = Field(
        default="postgresql+asyncpg://postgres:gongan2024@localhost:5432/gongan_memory",
        alias="POSTGRES_URL",
    )


class LLMSettings(_EnvBase):
    """LLM 双路由配置（阿里云百炼：qwen-flash 主用 + qwen-plus 兜底）。"""

    api_key: str = Field(default="sk-your-api-key", alias="LLM_API_KEY")
    fallback_api_key: str = Field(default="", alias="LLM_FALLBACK_API_KEY")
    base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="LLM_BASE_URL",
    )
    fallback_base_url: str = Field(default="", alias="LLM_FALLBACK_BASE_URL")
    model: str = Field(default="qwen3.8-flash", alias="LLM_MODEL")
    fallback_model: str = Field(default="qwen3.7-flash-2026-07-15", alias="LLM_FALLBACK_MODEL")
    timeout_seconds: float = Field(default=60.0, alias="LLM_TIMEOUT_SECONDS")
    max_retries: int = Field(default=2, alias="LLM_MAX_RETRIES")


class EmbeddingSettings(_EnvBase):
    """本地 embedding / reranker / classifier 模型配置。

    模型权重复用本地 edu_agent_project 检出目录（无需重新下载）。
    """

    bge_m3_path: str = Field(
        default=r"E:\BaiduNetdiskDownload\zengke\code\edu_rag\rag_qa\models\bge-m3",
        alias="BGE_M3_PATH",
    )
    reranker_path: str = Field(
        default=r"E:\BaiduNetdiskDownload\zengke\code\edu_rag\rag_qa\models\bge-reranker-large",
        alias="RERANKER_PATH",
    )
    classifier_path: str = Field(
        default=r"E:\BaiduNetdiskDownload\zengke\code\edu_agent_project\backend\models\classifier\query-classifier-finetuned",
        alias="CLASSIFIER_PATH",
    )
    dense_dim: int = Field(default=1024, alias="EMBEDDING_DENSE_DIM")


class JwtSettings(_EnvBase):
    """JWT 认证配置。"""

    secret: str = Field(default="change-me-in-production", alias="JWT_SECRET")
    algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    expire_minutes: int = Field(default=720, alias="JWT_EXPIRE_MINUTES")


class CorsSettings(_EnvBase):
    """CORS 允许的来源。"""

    origins: Annotated[list[str], NoDecode, BeforeValidator(_split_origins)] = Field(
        default=["http://localhost:5173", "http://localhost:3000"],
        alias="CORS_ORIGINS",
    )


class ObservabilitySettings(_EnvBase):
    """Langfuse / 监控配置。"""

    langfuse_public_key: str = Field(default="", alias="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: str = Field(default="", alias="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", alias="LANGFUSE_HOST")


class Settings(_EnvBase):
    """应用根配置。"""

    env: str = Field(default="dev", alias="ENV")
    app_name: str = "工安卫士"
    app_version: str = "0.1.0"
    debug: bool = Field(default=True, alias="DEBUG")

    mysql: MysqlSettings = Field(default_factory=MysqlSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    milvus: MilvusSettings = Field(default_factory=MilvusSettings)
    neo4j: Neo4jSettings = Field(default_factory=Neo4jSettings)
    postgres: PostgresSettings = Field(default_factory=PostgresSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    jwt: JwtSettings = Field(default_factory=JwtSettings)
    cors: CorsSettings = Field(default_factory=CorsSettings)
    observability: ObservabilitySettings = Field(default_factory=ObservabilitySettings)


@lru_cache
def get_settings() -> Settings:
    """返回缓存的应用配置单例。"""
    return Settings()
