"""认证相关 DTO —— 与冻结的 ``frontend/openapi.json`` 契约保持一致。"""

from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

# 密码策略：8-128 位，必须至少包含一个字母和一个数字。
_PWD_LETTER = re.compile(r"[A-Za-z]")
_PWD_DIGIT = re.compile(r"\d")


def _validate_password_complexity(password: str) -> str:
    """强制执行密码策略：长度 >= 8，必须同时包含字母和数字。"""
    if not _PWD_LETTER.search(password) or not _PWD_DIGIT.search(password):
        raise ValueError(
            "Password must contain at least one letter and one digit"
        )
    return password


class LoginRequest(BaseModel):
    """POST /api/v1/auth/login 请求体。"""

    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _check_pwd(cls, v: str) -> str:
        return _validate_password_complexity(v)


class RefreshResponse(BaseModel):
    """POST /api/v1/auth/refresh 响应。"""

    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    """POST /api/v1/auth/register 请求体。"""

    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    real_name: str = Field(min_length=1, max_length=64)
    position: str = Field(min_length=1, max_length=32)
    role: str = Field(default="worker")

    @field_validator("password")
    @classmethod
    def _check_pwd(cls, v: str) -> str:
        return _validate_password_complexity(v)


class AdminUserResponse(BaseModel):
    """认证端点返回的用户公开字段。"""

    id: int
    username: str
    real_name: str
    position: str
    role: str


class LoginResponse(BaseModel):
    """POST /api/v1/auth/login 响应。"""

    access_token: str
    token_type: str = "bearer"
    user: AdminUserResponse


class RegisterResponse(BaseModel):
    """POST /api/v1/auth/register 响应。"""

    id: int
    username: str
    position: str
    role: str
