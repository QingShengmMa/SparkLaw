"""Account registration, login, and usage endpoints."""

from __future__ import annotations

import sqlite3
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.auth.dependencies import AuthUser, optional_user, require_user
from app.auth.security import hash_password, verify_password
from app.auth.store import auth_store
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["账号"])


class AuthUserResponse(BaseModel):
    id: int
    email: str
    display_name: str
    role: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    registration_enabled: bool
    bootstrap_required: bool
    user: Optional[AuthUserResponse] = None


class AuthResponse(BaseModel):
    user: AuthUserResponse
    usage: dict


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=1)
    display_name: str = Field(default="SparkLaw 用户", max_length=40)
    invite_code: Optional[str] = Field(default=None, max_length=120)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise ValueError("请输入有效邮箱。")
        return email


class LoginRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise ValueError("请输入有效邮箱。")
        return email


def _registration_enabled() -> bool:
    return auth_store.user_count() == 0 or settings.AUTH_ALLOW_REGISTRATION


def _to_user_response(user: AuthUser | dict) -> AuthUserResponse:
    if isinstance(user, AuthUser):
        return AuthUserResponse(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            role=user.role,
        )
    return AuthUserResponse(
        id=int(user["id"]),
        email=str(user["email"]),
        display_name=str(user["display_name"]),
        role=str(user["role"]),
    )


def _set_session_cookie(response: Response, token: str, max_age: int) -> None:
    response.set_cookie(
        settings.AUTH_COOKIE_NAME,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.AUTH_COOKIE_SECURE,
        samesite=settings.AUTH_COOKIE_SAMESITE,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(settings.AUTH_COOKIE_NAME, path="/")


@router.get("/status", response_model=AuthStatusResponse)
async def auth_status(user: Optional[AuthUser] = Depends(optional_user)):
    return AuthStatusResponse(
        authenticated=user is not None,
        registration_enabled=_registration_enabled(),
        bootstrap_required=auth_store.user_count() == 0,
        user=_to_user_response(user) if user else None,
    )


@router.post("/register", response_model=AuthResponse)
async def register(payload: RegisterRequest, response: Response):
    if not _registration_enabled():
        raise HTTPException(status_code=403, detail="当前站点暂未开放新用户注册。")
    if len(payload.password) < settings.AUTH_PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"密码至少需要 {settings.AUTH_PASSWORD_MIN_LENGTH} 位。",
        )
    if settings.AUTH_REGISTRATION_INVITE_CODE:
        if payload.invite_code != settings.AUTH_REGISTRATION_INVITE_CODE:
            raise HTTPException(status_code=403, detail="邀请码不正确。")

    role = "admin" if auth_store.user_count() == 0 else "user"
    try:
        user = auth_store.create_user(
            email=payload.email,
            display_name=payload.display_name or payload.email.split("@", 1)[0],
            password_hash=hash_password(payload.password),
            role=role,
        )
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="这个邮箱已经注册过。") from None

    token, expires_at = auth_store.create_session(int(user["id"]))
    seconds = int(expires_at.timestamp() - time.time())
    _set_session_cookie(response, token, seconds)
    return AuthResponse(
        user=_to_user_response(user),
        usage=auth_store.usage_summary(int(user["id"])),
    )


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, response: Response):
    user = auth_store.get_user_by_email(payload.email)
    if not user or not verify_password(payload.password, str(user["password_hash"])):
        raise HTTPException(status_code=401, detail="邮箱或密码不正确。")
    if user["status"] != "active":
        raise HTTPException(status_code=403, detail="账号已停用。")

    token, expires_at = auth_store.create_session(int(user["id"]))
    seconds = int(expires_at.timestamp() - time.time())
    _set_session_cookie(response, token, seconds)
    return AuthResponse(
        user=_to_user_response(user),
        usage=auth_store.usage_summary(int(user["id"])),
    )


@router.post("/logout")
async def logout(request: Request, response: Response):
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if token:
        auth_store.revoke_session(token)
    _clear_session_cookie(response)
    return {"success": True}


@router.get("/me", response_model=AuthResponse)
async def me(user: AuthUser = Depends(require_user)):
    return AuthResponse(
        user=_to_user_response(user),
        usage=auth_store.usage_summary(user.id),
    )


@router.get("/usage")
async def usage(user: AuthUser = Depends(require_user)):
    return auth_store.usage_summary(user.id)
