"""认证接口：login / register / me / refresh。

与 ``frontend/openapi.json`` 契约对齐。除 ``/auth/login`` 和
``/auth/register`` 外，所有接口均要求有效的 Bearer JWT。
"""

from __future__ import annotations

from fastapi import APIRouter, Header, status
from sqlalchemy import select

from app.config import get_settings
from app.core.deps import CurrentUser, DbSession
from app.core.exceptions import AuthError, ConflictError, ValidationError
from app.core.logger import get_logger
from app.core.redis import get_redis
from app.core.security import (
    create_access_token,
    pwd_hash,
    pwd_verify,
)
from app.models.user import User
from app.schemas.auth import (
    AdminUserResponse,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
    RegisterRequest,
    RegisterResponse,
)
from app.services.audit.logger import (
    ACTION_AUTH_LOGIN,
    ACTION_AUTH_REGISTER,
    audit_log,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["认证"])

# Refresh token 轮换：将旧 jti 加入黑名单，时长为 token 剩余有效期。
# Key: ``jwt:blacklist:{jti}``  TTL: token exp - now（秒）
REFRESH_BLACKLIST_TTL = 86400  # 24 小时上限


async def _user_to_response(user: User) -> AdminUserResponse:
    """将 User ORM 行序列化为公开 DTO。"""
    return AdminUserResponse(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        position=user.position.value if hasattr(user.position, "value") else str(user.position),
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: DbSession,
    x_forwarded_for: str | None = Header(default=None),
) -> LoginResponse:
    """认证并签发 JWT — 无需认证。"""
    settings = get_settings()
    stmt = select(User).where(User.username == payload.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    ip = x_forwarded_for.split(",")[0].strip() if x_forwarded_for else None

    if user is None or not pwd_verify(payload.password, user.password_hash):
        # 登录失败也要记审计 — 不暴露到底是用户名还是密码错误。
        if user is not None:
            await audit_log(
                user_id=user.id,
                username=user.username,
                action=ACTION_AUTH_LOGIN,
                status="failure",
                ip_address=ip,
                detail={"reason": "wrong_password"},
            )
        raise AuthError("Invalid username or password")

    token = create_access_token(
        user.id,
        user.position.value if hasattr(user.position, "value") else str(user.position),
        user.role.value if hasattr(user.role, "value") else str(user.role),
        secret=settings.jwt.secret,
        algorithm=settings.jwt.algorithm,
        expire_minutes=settings.jwt.expire_minutes,
    )
    logger.info("User %s logged in", user.username)

    await audit_log(
        user_id=user.id,
        username=user.username,
        action=ACTION_AUTH_LOGIN,
        resource_type="auth",
        status="success",
        ip_address=ip,
    )

    return LoginResponse(
        access_token=token,
        user=await _user_to_response(user),
    )


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, db: DbSession) -> RegisterResponse:
    """创建新用户账号 — 无需认证。"""
    stmt = select(User).where(User.username == payload.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        raise ConflictError(f"Username '{payload.username}' already exists")

    if payload.role not in ("worker", "admin"):
        raise ValidationError("Role must be 'worker' or 'admin'")

    user = User(
        username=payload.username,
        password_hash=pwd_hash(payload.password),
        real_name=payload.real_name,
        position=payload.position,
        role=payload.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info("User %s registered (role=%s)", user.username, user.role)

    await audit_log(
        user_id=user.id,
        username=user.username,
        action=ACTION_AUTH_REGISTER,
        resource_type="auth",
        detail={"role": user.role.value if hasattr(user.role, "value") else str(user.role)},
    )

    return RegisterResponse(
        id=user.id,
        username=user.username,
        position=user.position.value if hasattr(user.position, "value") else str(user.position),
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )


@router.get("/me", response_model=AdminUserResponse)
async def get_me(user: CurrentUser, db: DbSession) -> AdminUserResponse:
    """返回当前已认证用户 — 需要 Bearer JWT。"""
    stmt = select(User).where(User.id == user["user_id"])
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()
    if db_user is None:
        raise AuthError("User not found")
    return await _user_to_response(db_user)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(user: CurrentUser) -> RefreshResponse:
    """基于当前 token claims 签发新 JWT。

    Token 轮换：旧 jti 会在 Redis 中拉黑 24 小时，
    因此刷新后重放旧 token 会被拒绝。
    """
    settings = get_settings()
    redis = get_redis()
    old_jti = user.get("jti")
    if old_jti:
        await redis.set(
            f"jwt:blacklist:{old_jti}", "1", ex=REFRESH_BLACKLIST_TTL
        )

    token = create_access_token(
        user["user_id"],
        user.get("position", ""),
        user.get("role", "worker"),
        secret=settings.jwt.secret,
        algorithm=settings.jwt.algorithm,
        expire_minutes=settings.jwt.expire_minutes,
    )
    return RefreshResponse(access_token=token)
