"""llm_guard 结构化输出测试：重试、校验、降级。"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.services.llm.client import LLMResponse
from app.services.llm.llm_guard import GuardedOutputError, guarded_json_call


class Out(BaseModel):
    value: int


class OkLLM:
    async def chat(self, messages, temperature=0.3, max_tokens=1024):
        return LLMResponse(content='{"value": 1}', route="mock", model="fake")


class FlakyLLM:
    """前两次校验失败，之后产出合法 JSON。"""

    def __init__(self) -> None:
        self.calls = 0

    async def chat(self, messages, temperature=0.3, max_tokens=1024):
        self.calls += 1
        if self.calls <= 2:
            return LLMResponse(content="not json at all", route="mock", model="fake")
        return LLMResponse(content='{"value": 42}', route="mock", model="fake")


class AlwaysBadLLM:
    async def chat(self, messages, temperature=0.3, max_tokens=1024):
        return LLMResponse(content='{"wrong": "schema"}', route="mock", model="fake")


@pytest.mark.asyncio
async def test_guard_first_try_success():
    out = await guarded_json_call(OkLLM(), [], Out)
    assert out.value == 1


@pytest.mark.asyncio
async def test_guard_retries_then_succeeds():
    llm = FlakyLLM()
    out = await guarded_json_call(llm, [], Out)
    assert out.value == 42
    assert llm.calls == 3


@pytest.mark.asyncio
async def test_guard_degrades_to_fallback():
    out = await guarded_json_call(AlwaysBadLLM(), [], Out, fallback=Out(value=7))
    assert out.value == 7


@pytest.mark.asyncio
async def test_guard_raises_without_fallback():
    with pytest.raises(GuardedOutputError):
        await guarded_json_call(AlwaysBadLLM(), [], Out, max_retries=1)
