"""Langfuse 辅助函数：默认关闭的行为 + None 安全性。"""

from types import SimpleNamespace

from app.core import langfuse as lf


def _fake_settings(enabled: bool) -> SimpleNamespace:
    return SimpleNamespace(
        observability=SimpleNamespace(
            langfuse_public_key="pk-test" if enabled else "",
            langfuse_secret_key="sk-test" if enabled else "",
            langfuse_host="http://localhost:3000",
        )
    )


def test_disabled_when_keys_empty(monkeypatch):
    monkeypatch.setattr(lf, "get_settings", lambda: _fake_settings(False))
    assert lf.langfuse_enabled() is False
    assert lf.get_langfuse() is None


def test_enabled_requires_both_keys(monkeypatch):
    monkeypatch.setattr(lf, "get_settings", lambda: _fake_settings(True))
    assert lf.langfuse_enabled() is True


def test_helpers_noop_without_trace(monkeypatch):
    """tracing 关闭时所有辅助函数应降级为空操作。"""
    monkeypatch.setattr(lf, "get_settings", lambda: _fake_settings(False))
    assert lf.lf_start_span(None, "retrieval") is None
    assert lf.lf_start_generation(None, "chat-completion") is None
    with lf.lf_trace("safety-qa", user_id="1", session_id="abc") as trace:
        assert trace is None
    lf.lf_end_span(None)
    lf.lf_finish_generation(None, output="ok")
    lf.lf_fail_generation(None, "boom")
    lf.flush_langfuse()
