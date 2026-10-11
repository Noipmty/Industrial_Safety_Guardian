"""Langfuse LLM 可观测性 — 通过 LANGFUSE_* 配置项选择性开启。

每个辅助函数都是防御式的：当密钥未配置（或 SDK 出现异常）时，
tracing 会降级为空操作，业务逻辑永远不会因此失败。

埋点位置：
    - 每个 QA / 考试请求一个 trace（service / API 层）；
    - 并行工具执行外层包一个 ``retrieval`` span；
    - 每次 LLM 路由调用一个 ``generation`` span（input/output/usage/route）。
"""

from __future__ import annotations

import atexit
from contextlib import contextmanager
from typing import Any

from app.config import get_settings
from app.core.logger import get_logger, get_trace_id

logger = get_logger(__name__)

_client: Any | None = None
_init_done = False
# 请求 trace-id -> 存活的 Langfuse trace 句柄（让同一请求内嵌套的
# span/generation 归并到同一个 trace，而不是各起一个）。
_active_traces: dict[str, Any] = {}


def langfuse_enabled() -> bool:
    """两个 Langfuse 密钥均已配置时返回 True。"""
    obs = get_settings().observability
    return bool(obs.langfuse_public_key and obs.langfuse_secret_key)


def get_langfuse() -> Any | None:
    """惰性初始化的 Langfuse 客户端，未启用时返回 None。"""
    global _client, _init_done
    if not langfuse_enabled():
        return None
    if not _init_done:
        _init_done = True
        try:
            from langfuse import Langfuse

            obs = get_settings().observability
            _client = Langfuse(
                public_key=obs.langfuse_public_key,
                secret_key=obs.langfuse_secret_key,
                host=obs.langfuse_host,
            )
            atexit.register(_safe_flush)
            logger.info("Langfuse tracing enabled (host=%s)", obs.langfuse_host)
        except Exception:  # noqa: BLE001 — tracing 绝不能破坏业务流程
            logger.warning("Langfuse init failed; tracing disabled", exc_info=True)
            _client = None
    return _client


def _safe_flush() -> None:
    if _client is not None:
        try:
            _client.flush()
        except Exception:  # noqa: BLE001
            logger.debug("Langfuse flush failed", exc_info=True)


def flush_langfuse() -> None:
    """刷新待上报事件（短生命周期脚本中调用）。"""
    _safe_flush()


def _get_or_create_trace() -> Any | None:
    """返回当前请求的 trace 句柄，必要时新建一个。"""
    if not langfuse_enabled():
        return None
    tid = get_trace_id()
    existing = _active_traces.get(tid)
    if existing is not None:
        return existing
    lf = get_langfuse()
    if lf is None:
        return None
    try:
        trace = lf.trace(id=tid, name="llm-call")
    except Exception:  # noqa: BLE001
        logger.debug("Langfuse trace creation failed", exc_info=True)
        return None
    _active_traces[tid] = trace
    return trace


@contextmanager
def lf_trace(
    name: str,
    *,
    user_id: str = "",
    session_id: str = "",
    metadata: dict[str, Any] | None = None,
):
    """将命名 trace 绑定到当前请求 trace id（yield 出句柄）。"""
    trace = None
    lf = get_langfuse()
    if lf is not None:
        try:
            trace = lf.trace(
                id=get_trace_id(),
                name=name,
                user_id=user_id or None,
                session_id=session_id or None,
                metadata=metadata or {},
            )
            _active_traces[get_trace_id()] = trace
        except Exception:  # noqa: BLE001
            logger.debug("Langfuse trace creation failed", exc_info=True)
    try:
        yield trace
    finally:
        if trace is not None:
            _active_traces.pop(get_trace_id(), None)


def lf_start_span(
    trace: Any, name: str, metadata: dict[str, Any] | None = None
) -> Any | None:
    """启动子 span；trace 为 None 时惰性绑定到请求 trace。"""
    if trace is None and not langfuse_enabled():
        return None
    try:
        target = trace if trace is not None else _get_or_create_trace()
        if target is None:
            return None
        return target.span(name=name, metadata=metadata or {})
    except Exception:  # noqa: BLE001
        logger.debug("Langfuse span start failed", exc_info=True)
        return None


def lf_end_span(span: Any) -> None:
    """结束一个 span（对 None 安全）。"""
    if span is None:
        return
    try:
        span.end()
    except Exception:  # noqa: BLE001
        logger.debug("Langfuse span end failed", exc_info=True)


def lf_start_generation(
    trace: Any,
    name: str,
    *,
    model: str = "",
    input: Any = None,
    metadata: dict[str, Any] | None = None,
) -> Any | None:
    """启动 LLM generation span；惰性绑定到请求 trace。"""
    if trace is None and not langfuse_enabled():
        return None
    try:
        target = trace if trace is not None else _get_or_create_trace()
        if target is None:
            return None
        return target.generation(
            name=name, model=model or None, input=input, metadata=metadata or {}
        )
    except Exception:  # noqa: BLE001
        logger.debug("Langfuse generation start failed", exc_info=True)
        return None


def lf_finish_generation(
    gen: Any, *, output: Any = None, usage: dict[str, Any] | None = None
) -> None:
    """在 generation span 上记录成功输出与 token 用量。"""
    if gen is None:
        return
    try:
        gen.update(output=output, usage=usage or {}, level="DEFAULT")
        gen.end()
    except Exception:  # noqa: BLE001
        logger.debug("Langfuse generation finish failed", exc_info=True)


def lf_fail_generation(gen: Any, error: str) -> None:
    """在 generation span 上记录失败。"""
    if gen is None:
        return
    try:
        gen.update(level="ERROR", status_message=error[:500])
        gen.end()
    except Exception:  # noqa: BLE001
        logger.debug("Langfuse generation fail failed", exc_info=True)
