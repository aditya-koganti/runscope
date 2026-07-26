from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.config import Settings, get_settings
from runscope_api.db import get_session
from runscope_api.errors import AppError
from runscope_api.models import Role, User

password_hasher = PasswordHash.recommended()
bearer_scheme = HTTPBearer(auto_error=False)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user: User, settings: Settings | None = None) -> tuple[str, int]:
    active_settings = settings or get_settings()
    expires_delta = timedelta(minutes=active_settings.access_token_minutes)
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "role": user.role.value,
        "iss": active_settings.jwt_issuer,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(payload, active_settings.jwt_secret, algorithm="HS256")
    return token, int(expires_delta.total_seconds())


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("authentication_required", "Authentication is required", 401)
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
        )
        user_id = UUID(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise AppError("invalid_access_token", "Access token is invalid or expired", 401) from exc
    user = await session.scalar(select(User).where(User.id == user_id))
    if user is None:
        raise AppError("invalid_access_token", "Access token is invalid or expired", 401)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed: Role) -> Callable[[User], Awaitable[User]]:
    async def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise AppError(
                "permission_denied",
                "Your role does not permit this action",
                403,
                {"required_roles": [role.value for role in allowed]},
            )
        return user

    return dependency


ResearcherUser = Annotated[
    User,
    Depends(require_roles(Role.RESEARCHER, Role.ADMINISTRATOR)),
]
AdministratorUser = Annotated[User, Depends(require_roles(Role.ADMINISTRATOR))]
