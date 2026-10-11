"""应用统一的异常体系。"""

from __future__ import annotations


class AppError(Exception):
    """所有应用异常的基类。"""

    code: str = "APP_ERROR"
    message: str = "Internal application error"
    status_code: int = 500

    def __init__(self, message: str | None = None, *, code: str | None = None) -> None:
        if message is not None:
            self.message = message
        if code is not None:
            self.code = code
        super().__init__(self.message)


class NotFoundError(AppError):
    """请求的资源不存在。"""

    code = "NOT_FOUND"
    message = "Resource not found"
    status_code = 404


class AuthError(AppError):
    """认证失败（凭证缺失 / 无效 / 过期）。"""

    code = "UNAUTHORIZED"
    message = "Authentication failed"
    status_code = 401


class PermissionError_(AppError):
    """已认证但无权执行该操作。"""

    code = "FORBIDDEN"
    message = "Permission denied"
    status_code = 403


class ValidationError(AppError):
    """请求载荷未通过校验。"""

    code = "VALIDATION_ERROR"
    message = "Request validation failed"
    status_code = 422


class ConflictError(AppError):
    """资源状态冲突（重复提交、锁过期等）。"""

    code = "CONFLICT"
    message = "Resource conflict"
    status_code = 409


class LLMError(AppError):
    """LLM 调用重试后仍失败（超时、输出异常、服务商错误）。"""

    code = "LLM_ERROR"
    message = "LLM service error"
    status_code = 503


class RetrievalError(AppError):
    """检索后端（Milvus / Neo4j）失败或降级。"""

    code = "RETRIEVAL_ERROR"
    message = "Retrieval service error"
    status_code = 503


class StorageError(AppError):
    """数据库 / 缓存存储故障。"""

    code = "STORAGE_ERROR"
    message = "Storage service error"
    status_code = 503
