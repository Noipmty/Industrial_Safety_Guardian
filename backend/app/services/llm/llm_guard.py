"""所有 LLM 调用的结构化输出守卫。

``guarded_json_call`` 在 ``LLMClient.chat`` 之上提供：
1. 用 Pydantic schema 校验解析后的 JSON；
2. 解析/校验失败时进行有限次数重试（默认 <= 2）；
3. 优雅降级 —— 调用方提供 fallback 工厂，使工作流在
   LLM 不可用时仍有确定性路径可走。
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from app.core.logger import get_logger
from app.services.llm.client import LLMClient

logger = get_logger(__name__)

MAX_GUARD_RETRIES = 2

# Pydantic 模型类型变量（bound 到 BaseModel）。
T = TypeVar("T", bound=BaseModel)


class GuardedOutputError(Exception):
    """重试次数耗尽且未提供 fallback。"""


async def guarded_json_call(
    client: LLMClient,
    messages: list[dict[str, str]],
    schema: type[T],
    *,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    max_retries: int = MAX_GUARD_RETRIES,
    fallback: T | None = None,
) -> T:
    """调用 LLM，按 ``schema`` 校验，失败则重试，最后降级。

    仅当 ``fallback`` 为 None 时才抛出 :class:`GuardedOutputError`。
    """
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            resp = await client.chat(
                messages, temperature=temperature, max_tokens=max_tokens
            )
            data = resp.json()
            return schema.model_validate(data)
        except (ValueError, KeyError, PydanticValidationError) as exc:
            last_error = exc
            logger.warning(
                "llm_guard validation failed (attempt %s/%s): %s",
                attempt + 1,
                max_retries + 1,
                exc,
            )
        except RuntimeError as exc:
            # 路由层传输失败（超时 / HTTP 错误 / LLMClient 抛出的
            # 重试耗尽）—— 降级处理，而不是直接 500。
            last_error = exc
            logger.warning("llm_guard route failure (attempt %s): %s", attempt + 1, exc)
    if fallback is not None:
        logger.info("llm_guard degraded to fallback output")
        return fallback
    raise GuardedOutputError(str(last_error)) from last_error
