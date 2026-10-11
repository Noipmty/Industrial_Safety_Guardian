"""所有 API 端点通用的响应 DTO。"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """所有 API 响应的标准包装结构。

    Attributes:
        code: 业务状态码（0 = 成功，非零 = 出错）。
        message: 人类可读的状态信息。
        data: 响应数据载荷，类型由 ``DataT`` 指定。
        trace_id: 用于请求关联的分布式追踪标识符。
    """

    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="success", description="提示信息")
    data: DataT | None = Field(default=None, description="响应数据")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")


class PaginatedResponse(BaseModel, Generic[DataT]):
    """分页列表响应。

    Attributes:
        items: 当前页的数据列表。
        total: 符合查询条件的总记录数。
        page: 当前页码（从 1 开始）。
        page_size: 每页条数。
    """

    items: list[DataT] = Field(description="当前页数据列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码（从 1 开始）")
    page_size: int = Field(description="每页条数")
