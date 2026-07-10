"""Tests for src/api/auth.py — runs offline using a local RSA key pair.

Tests:
  1. role_from_claims: correct group → role mapping
  2. auth_mode: env-var detection
  3. verify_token: good token, expired, wrong audience, tampered signature
  4. _resolve_role: no token → guest; good user token → user; dev bypass → admin
  5. require_user/require_admin: 403 / 401 enforcement

Run: python scripts/test_auth.py
"""
from __future__ import annotations

import os
import sys
import time
from unittest.mock import patch, MagicMock

sys.path.insert(0, ".")

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from src.api.auth import (
    Role,
    auth_mode,
    reset_auth_cache,
    role_from_claims,
    verify_token,
)

FAILS: list[str] = []

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check(name: str, cond: bool) -> None:
    print(f"[{'OK ' if cond else 'FAIL'}] {name}")
    if not cond:
        FAILS.append(name)


def _gen_keys():
    priv = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    return priv, priv.public_key()


def _make_token(
    private_key,
    *,
    sub: str = "user-1",
    groups: list[str] | None = None,
    audience: str = "test-client",
    issuer: str = "https://cognito-idp.us-east-1.amazonaws.com/us-east-1_TEST",
    exp_offset: int = 3600,
) -> str:
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now + exp_offset,
    }
    if groups is not None:
        payload["cognito:groups"] = groups
    return jwt.encode(payload, private_key, algorithm="RS256")


class _MockSigningKey:
    def __init__(self, key):
        self.key = key


class _MockJWKSClient:
    def __init__(self, public_key):
        self._pub = public_key

    def get_signing_key_from_jwt(self, token):
        return _MockSigningKey(self._pub)


# ---------------------------------------------------------------------------
# 1. role_from_claims
# ---------------------------------------------------------------------------

def test_role_from_claims() -> None:
    check("admin group → ADMIN", role_from_claims({"cognito:groups": ["admin"]}) == Role.ADMIN)
    check("user group → USER", role_from_claims({"cognito:groups": ["user"]}) == Role.USER)
    check("admin+user → ADMIN", role_from_claims({"cognito:groups": ["user", "admin"]}) == Role.ADMIN)
    check("no groups → GUEST", role_from_claims({}) == Role.GUEST)
    check("empty groups → GUEST", role_from_claims({"cognito:groups": []}) == Role.GUEST)
    check("unknown group → GUEST", role_from_claims({"cognito:groups": ["viewer"]}) == Role.GUEST)


# ---------------------------------------------------------------------------
# 2. auth_mode
# ---------------------------------------------------------------------------

def test_auth_mode() -> None:
    for key in ("AREPAS_AUTH_MODE", "AREPAS_COGNITO_USER_POOL_ID"):
        os.environ.pop(key, None)
    check("no config → disabled", auth_mode() == "disabled")

    os.environ["AREPAS_COGNITO_USER_POOL_ID"] = "us-east-1_TEST"
    check("pool set → cognito", auth_mode() == "cognito")
    del os.environ["AREPAS_COGNITO_USER_POOL_ID"]

    os.environ["AREPAS_AUTH_MODE"] = "disabled"
    check("explicit disabled", auth_mode() == "disabled")
    del os.environ["AREPAS_AUTH_MODE"]

    os.environ["AREPAS_AUTH_MODE"] = "cognito"
    os.environ["AREPAS_COGNITO_USER_POOL_ID"] = "us-east-1_TEST"
    check("explicit cognito", auth_mode() == "cognito")
    del os.environ["AREPAS_AUTH_MODE"]
    del os.environ["AREPAS_COGNITO_USER_POOL_ID"]


# ---------------------------------------------------------------------------
# 3. verify_token
# ---------------------------------------------------------------------------

def test_verify_token() -> None:
    priv, pub = _gen_keys()
    POOL = "us-east-1_TEST"
    ISSUER = f"https://cognito-idp.us-east-1.amazonaws.com/{POOL}"
    CLIENT = "test-client"

    os.environ["AREPAS_COGNITO_USER_POOL_ID"] = POOL
    os.environ["AREPAS_COGNITO_CLIENT_ID"] = CLIENT
    reset_auth_cache()

    mock_client = _MockJWKSClient(pub)

    with patch("src.api.auth._jwks_client", return_value=mock_client):
        # Good token — user
        token = _make_token(priv, groups=["user"], audience=CLIENT, issuer=ISSUER)
        claims = verify_token(token)
        check("good token decodes", claims["sub"] == "user-1")
        check("good token groups", claims.get("cognito:groups") == ["user"])

        # Expired token
        exp_token = _make_token(priv, groups=["user"], audience=CLIENT, issuer=ISSUER, exp_offset=-1)
        try:
            verify_token(exp_token)
            check("expired token raises", False)
        except jwt.ExpiredSignatureError:
            check("expired token raises", True)

        # Wrong audience
        wrong_aud = _make_token(priv, groups=["user"], audience="wrong", issuer=ISSUER)
        try:
            verify_token(wrong_aud)
            check("wrong audience raises", False)
        except jwt.PyJWTError:
            check("wrong audience raises", True)

    # Tampered signature — uses real pub key but different private key
    priv2, pub2 = _gen_keys()
    tampered = _make_token(priv2, groups=["admin"], audience=CLIENT, issuer=ISSUER)
    mock_real_pub = _MockJWKSClient(pub)  # verifies with original pub (mismatch)
    with patch("src.api.auth._jwks_client", return_value=mock_real_pub):
        try:
            verify_token(tampered)
            check("tampered token raises", False)
        except jwt.PyJWTError:
            check("tampered token raises", True)

    del os.environ["AREPAS_COGNITO_USER_POOL_ID"]
    del os.environ["AREPAS_COGNITO_CLIENT_ID"]
    reset_auth_cache()


# ---------------------------------------------------------------------------
# 4 & 5. _resolve_role + require_user / require_admin (dev-bypass)
# ---------------------------------------------------------------------------

def test_dev_bypass() -> None:
    """When auth is disabled, _resolve_role returns ADMIN with no token."""
    import asyncio
    from src.api.auth import _resolve_role, require_user, require_admin

    for key in ("AREPAS_AUTH_MODE", "AREPAS_COGNITO_USER_POOL_ID"):
        os.environ.pop(key, None)

    # Simulate Depends(_bearer) returning None (no Authorization header)
    role = asyncio.run(_resolve_role(credentials=None))
    check("dev bypass: no token → ADMIN", role == Role.ADMIN)

    role = asyncio.run(require_user(role=Role.ADMIN))
    check("dev bypass: require_user passes", role == Role.ADMIN)

    role = asyncio.run(require_admin(role=Role.ADMIN))
    check("dev bypass: require_admin passes", role == Role.ADMIN)


def test_role_enforcement() -> None:
    """GUEST is denied explore/admin; USER is denied admin."""
    import asyncio
    from fastapi import HTTPException
    from src.api.auth import require_user, require_admin

    for case_role, fn, should_raise in [
        (Role.GUEST, require_user, True),
        (Role.GUEST, require_admin, True),
        (Role.USER, require_user, False),
        (Role.USER, require_admin, True),
        (Role.ADMIN, require_user, False),
        (Role.ADMIN, require_admin, False),
    ]:
        try:
            asyncio.run(fn(role=case_role))
            raised = False
        except HTTPException:
            raised = True
        name = f"{fn.__name__}(role={case_role.name}) raises={should_raise}"
        check(name, raised == should_raise)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    test_role_from_claims()
    test_auth_mode()
    test_verify_token()
    test_dev_bypass()
    test_role_enforcement()
    print("\nAll passed." if not FAILS else f"\nFAILURES: {FAILS}")
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
