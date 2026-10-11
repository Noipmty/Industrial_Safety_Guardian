"""统一 LLM 客户端：DeepSeek 为主路由 + Qwen 备用路由。

未配置真实 API key（默认 ``sk-your-api-key``）时，客户端降级为
确定性的 mock 行为，保证工作流在离线状态下仍可运行；
每次调用都会记录当前使用的路由。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_settings
from app.core import langfuse as lf
from app.core.logger import get_logger

logger = get_logger(__name__)

_DEFAULT_KEY = "sk-your-api-key"


@dataclass(slots=True)
class LLMResponse:
    """归一化后的补全结果。"""

    content: str
    route: str  # "primary" | "fallback" | "mock"
    model: str
    usage: dict[str, int] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.usage is None:
            self.usage = {}

    def json(self) -> Any:
        """把内容解析为 JSON，容忍代码围栏与 JSON 后的多余文本。"""
        text = self.content.strip()
        fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
        if fence:
            text = fence.group(1).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # 兜底 1：raw_decode 抓取第一个合法 JSON 值（容忍 "Extra data"）。
        try:
            value, _ = json.JSONDecoder().raw_decode(text.lstrip())
            return value
        except json.JSONDecodeError:
            pass
        # 兜底 2：抓取最外层的 JSON 对象/数组。
        match = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise json.JSONDecodeError("no JSON found", text, 0)


class LLMClient:
    """双路由聊天补全客户端（OpenAI 兼容 HTTP API）。"""

    def __init__(self) -> None:
        settings = get_settings()
        self._primary_key = settings.llm.api_key
        self._primary_base = settings.llm.base_url
        self._primary_model = settings.llm.model
        self._fallback_key = settings.llm.fallback_api_key
        self._fallback_base = settings.llm.fallback_base_url
        self._fallback_model = settings.llm.fallback_model
        self._timeout = settings.llm.timeout_seconds
        self._max_retries = settings.llm.max_retries

    @property
    def mock_mode(self) -> bool:
        """未配置真实 API key（为空或占位符）时为 True。"""
        return not self._primary_key or self._primary_key == _DEFAULT_KEY

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """执行一次聊天补全，路由失败时自动切换备用路由。"""
        if self.mock_mode:
            logger.info("LLM mock mode active, returning canned response")
            return LLMResponse(
                content=json.dumps(
                    {
                        "summary": "；".join(
                            m["content"][:60] for m in messages if m["role"] == "user"
                        )
                        or "（空会话）",
                        "mock": True,
                    },
                    ensure_ascii=False,
                ),
                route="mock",
                model="mock",
            )

        try:
            return await self._call_route(
                route="primary",
                base_url=self._primary_base,
                api_key=self._primary_key,
                model=self._primary_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as exc:  # noqa: BLE001 —— 故障切换（failover）正是本层职责
            logger.warning("Primary LLM route failed: %s", exc)

        if self._fallback_key and self._fallback_base:
            return await self._call_route(
                route="fallback",
                base_url=self._fallback_base,
                api_key=self._fallback_key,
                model=self._fallback_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        raise RuntimeError("Primary LLM failed and no fallback route configured")

    async def _call_route(
        self,
        route: str,
        base_url: str,
        api_key: str,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """调用一个 OpenAI 兼容端点，带有限次数重试。"""
        last_error: Exception | None = None
        gen = lf.lf_start_generation(
            None,
            "chat-completion",
            model=model,
            input=messages,
            metadata={"route": route, "base_url": base_url},
        )
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries + 1):
                try:
                    resp = await client.post(
                        f"{base_url.rstrip('/')}/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}"},
                        json={
                            "model": model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                        },
                    )
                    resp.raise_for_status()
                    payload = resp.json()
                    content = payload["choices"][0]["message"]["content"]
                    usage = payload.get("usage", {})
                    lf.lf_finish_generation(gen, output=content, usage=usage)
                    return LLMResponse(
                        content=content,
                        route=route,
                        model=model,
                        usage=usage,
                    )
                except Exception as exc:  # noqa: BLE001
                    last_error = exc
                    logger.warning(
                        "LLM %s attempt %s/%s failed: %s",
                        route,
                        attempt + 1,
                        self._max_retries + 1,
                        exc,
                    )
        lf.lf_fail_generation(gen, str(last_error))
        raise RuntimeError(f"LLM route '{route}' exhausted retries") from last_error


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """返回共享的 LLM 客户端单例。"""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
