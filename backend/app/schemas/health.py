"""健康检查响应 DTO。"""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """``/health`` 端点的响应模型。

    Attributes:
        status: 服务整体状态 —— ``ok``、``degraded`` 或 ``down``。
        version: 应用的语义化版本号字符串。
        checks: 组件名到其健康状态字符串的映射。
    """

    status: str = Field(description="服务整体状态：ok / degraded / down")
    version: str = Field(description="应用版本号")
    checks: dict[str, str] = Field(
        default_factory=dict,
        description="各组件健康检查结果，键为组件名、值为状态描述",
    )
