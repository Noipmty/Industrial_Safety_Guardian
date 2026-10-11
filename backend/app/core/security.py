"""JWT 签发 / 校验与密码哈希。"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.exceptions import AuthError
from app.core.logger import get_logger

logger = get_logger(__name__)

HASH_ROUNDS = 12


def create_access_token(
    user_id: int,
    position: str,
    role: str,
    *,
    secret: str,
    algorithm: str,
    expire_minutes: int,
) -> str:
    """为指定用户签发带签名的 JWT（含 jti 用于轮换追踪）。"""
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "position": position,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str) -> dict[str, Any]:
    """解码并校验 JWT。任何失败都会抛出 AuthError。"""
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired") from exc
    except jwt.InvalidTokenError as exc:
        logger.warning("Invalid JWT received")
        raise AuthError("Invalid token") from exc


def pwd_hash(password: str) -> str:
    """用 bcrypt 对明文密码进行哈希。"""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=HASH_ROUNDS))
    return hashed.decode("utf-8")


def pwd_verify(password: str, password_hash: str) -> bool:
    """用明文密码与存储的 bcrypt 哈希进行比对验证。"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False
