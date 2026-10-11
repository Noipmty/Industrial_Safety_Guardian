"""聊天相关 DTO —— 与冻结的 ``frontend/openapi.json`` 契约保持一致。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """POST /api/v1/chat 请求体。"""

    session_id: str | None = Field(default=None, description="会话ID，为空则新建")
    message: str = Field(min_length=1, description="用户消息")
    user_id: int = Field(description="用户ID（隐私隔离绑定位）")
    stream: bool = Field(default=False, description="是否SSE流式返回")
    scope: str | None = Field(
        default=None, description="问答视图：admin=管理端全库（仅管理员可用）"
    )


class ChatSource(BaseModel):
    """回答中引用的一条检索证据 chunk。"""

    doc_type: str = Field(description="来源文档类型")
    score: float = Field(description="检索得分")
    text: str = Field(description="原文片段")
    doc_id: int | None = Field(default=None, description="文档ID")
    chunk_id: str | None = Field(default=None, description="chunk标识")
    position: str | None = Field(default=None, description="章节位置")
    access_level: str | None = Field(
        default=None, description="文档权限等级 public/internal"
    )


class ChatResponse(BaseModel):
    """非流式聊天响应。"""

    response: str = Field(description="回答文本")
    intent: str = Field(description="查询类型 factual/relational/visual/structural")
    sources: list[ChatSource] = Field(default_factory=list, description="引用来源")
    session_id: str = Field(description="会话ID")
    trace_id: str = Field(description="链路追踪ID")


class ChatSession(BaseModel):
    """会话列表项。"""

    session_id: str
    last_message: str
    created_at: datetime
    updated_at: datetime


class ChatMessage(BaseModel):
    """一条历史消息。"""

    role: str = Field(pattern="^(user|assistant)$")
    content: str
    created_at: datetime
