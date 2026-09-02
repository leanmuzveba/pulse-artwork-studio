"""Authentication — email/password, sessions, verification (Phase 1, next step)."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes._stub import not_implemented

router = APIRouter()


@router.post("/register", summary="Create an account")
async def register() -> None:
    raise not_implemented("Registration")


@router.post("/login", summary="Log in and receive an access token")
async def login() -> None:
    raise not_implemented("Login")


@router.post("/refresh", summary="Exchange a refresh token for a new access token")
async def refresh() -> None:
    raise not_implemented("Token refresh")


@router.post("/password-reset", summary="Request a password reset email")
async def password_reset() -> None:
    raise not_implemented("Password reset")
