"""Unit tests for password hashing and JWT tokens (no DB needed)."""

from __future__ import annotations

import time

import jwt
import pytest

from app.core.security import (
    TOKEN_TYPE_ACCESS,
    TOKEN_TYPE_REFRESH,
    _create_token,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_verify_handles_garbage_hash():
    assert verify_password("whatever", "not-a-real-hash") is False


def test_access_token_roundtrip():
    token = create_access_token("user-123")
    claims = decode_token(token)
    assert claims["sub"] == "user-123"
    assert claims["type"] == TOKEN_TYPE_ACCESS


def test_refresh_token_type():
    claims = decode_token(create_refresh_token("user-123"))
    assert claims["type"] == TOKEN_TYPE_REFRESH


def test_expired_token_is_rejected():
    from datetime import timedelta

    token = _create_token("user-123", TOKEN_TYPE_ACCESS, timedelta(seconds=-1))
    time.sleep(0.01)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_tampered_token_is_rejected():
    token = create_access_token("user-123")
    with pytest.raises(jwt.PyJWTError):
        decode_token(token + "tamper")
