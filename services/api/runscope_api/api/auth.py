import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from runscope_api.db import get_session
from runscope_api.errors import AppError
from runscope_api.models import User
from runscope_api.schemas.auth import SignInRequest, TokenResponse, UserResponse
from runscope_api.security import (
    CurrentUser,
    create_access_token,
    normalize_email,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
logger = logging.getLogger(__name__)


@router.post("/sign-in", response_model=TokenResponse)
async def sign_in(
    body: SignInRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    user = await session.scalar(select(User).where(User.email == normalize_email(body.email)))
    if user is None or not verify_password(body.password, user.password_hash):
        raise AppError("invalid_credentials", "Email or password is incorrect", 401)
    logger.info("Authentication succeeded", extra={"user_id": str(user.id)})
    token, expires_in = create_access_token(user)
    return TokenResponse(
        access_token=token, expires_in=expires_in, user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def current_user(user: CurrentUser) -> User:
    return user
