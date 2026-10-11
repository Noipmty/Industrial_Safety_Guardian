"""配置测试。"""

import pytest


def test_default_env_is_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """未设置 ENV 时默认环境为 dev。"""
    monkeypatch.delenv("ENV", raising=False)
    from app.config import get_settings

    settings = get_settings()
    assert settings.env == "dev"


def test_jwt_secret_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """JWT secret 从环境变量读取。"""
    monkeypatch.setenv("JWT_SECRET", "test-secret-12345")
    from app.config import Settings

    settings = Settings()
    assert settings.jwt.secret == "test-secret-12345"  # noqa: S105 — 测试夹具


def test_cors_origins_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """CORS origins 被解析为列表。"""
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
    from app.config import Settings

    settings = Settings()
    assert "http://localhost:5173" in settings.cors.origins
    assert "http://localhost:3000" in settings.cors.origins


def test_llm_config_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """LLM 配置从环境变量读取。"""
    monkeypatch.setenv("LLM_API_KEY", "sk-test")
    monkeypatch.setenv("LLM_MODEL", "deepseek-chat")
    monkeypatch.setenv("LLM_FALLBACK_MODEL", "qwen-plus")
    from app.config import Settings

    settings = Settings()
    assert settings.llm.api_key == "sk-test"
    assert settings.llm.model == "deepseek-chat"
    assert settings.llm.fallback_model == "qwen-plus"


def test_database_urls_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """数据库 URL 从环境变量读取。"""
    monkeypatch.setenv("MYSQL_URL", "mysql+aiomysql://root:pass@localhost:3306/testdb")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    from app.config import Settings

    settings = Settings()
    assert settings.mysql.url == "mysql+aiomysql://root:pass@localhost:3306/testdb"
    assert settings.redis.url == "redis://localhost:6379/1"
