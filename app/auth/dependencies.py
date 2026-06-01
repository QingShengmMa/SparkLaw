"""FastAPI dependencies for authenticated routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator, Optional

from fastapi import Depends, HTTPException, Request, status

from app.auth.store import auth_store
from app.core.config import settings
from app.llm.usage_context import UsageContext, reset_usage_context, set_usage_context


@dataclass(frozen=True)
class AuthUser:
    id: int
    email: str
    display_name: str
    role: str
    status: str

    @classmethod
    def from_row(cls, row: dict) -> "AuthUser":
        return cls(
            id=int(row["id"]),
            email=str(row["email"]),
            display_name=str(row["display_name"]),
            role=str(row["role"]),
            status=str(row["status"]),
        )


async def optional_user(request: Request) -> Optional[AuthUser]:
    if not settings.AUTH_ENABLED:
        return AuthUser(
            id=0,
            email="local@sparklaw.dev",
            display_name="Local User",
            role="admin",
            status="active",
        )
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    row = auth_store.get_user_by_session(token or "")
    return AuthUser.from_row(row) if row else None


async def require_user(user: Optional[AuthUser] = Depends(optional_user)) -> AuthUser:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="请先登录后再使用 SparkLaw。",
        )
    return user


async def require_usage_context(
    request: Request,
    user: AuthUser = Depends(require_user),
) -> AsyncIterator[AuthUser]:
    token = set_usage_context(UsageContext(user_id=user.id, endpoint=request.url.path))
    try:
        yield user
    finally:
        reset_usage_context(token)
