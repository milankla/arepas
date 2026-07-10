"""JWT / Cognito authentication for the Arepas API.

Three roles (guest < user < admin) map to three FastAPI dependencies:

    require_guest   — inference (anonymous allowed)
    require_user    — explore (datasets, runs)
    require_admin   — train (Phase 5 endpoint)

Usage in routers::

    @router.post("/inference")
    async def run_inference(…, _role: Role = Depends(require_guest)):
        …

Or applied to a whole router at include time (2b)::

    app.include_router(datasets.router, dependencies=[Depends(require_user)])

Backend selection
-----------------
``AREPAS_AUTH_MODE=disabled`` (or unset + no Cognito pool configured) → every
request resolves as **admin** so local dev works unchanged.

``AREPAS_AUTH_MODE=cognito`` (or pool env auto-detected) → real JWT verification
against the pool's JWKS.

Required env vars when Cognito is active::

    AREPAS_COGNITO_USER_POOL_ID   e.g. us-east-1_Abc123
    AREPAS_COGNITO_CLIENT_ID      app client (audience claim)
"""
from __future__ import annotations

import enum
import os
from functools import lru_cache
from typing import Optional

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# ---------------------------------------------------------------------------
# Role
# ---------------------------------------------------------------------------

class Role(enum.IntEnum):
    GUEST = 0
    USER = 1
    ADMIN = 2


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def auth_mode() -> str:
    """Return ``'cognito'`` or ``'disabled'``."""
    explicit = os.environ.get("AREPAS_AUTH_MODE", "").lower()
    if explicit == "cognito":
        return "cognito"
    if explicit == "disabled":
        return "disabled"
    # Auto-detect: pool configured → cognito; otherwise dev bypass.
    return "cognito" if os.environ.get("AREPAS_COGNITO_USER_POOL_ID") else "disabled"


@lru_cache(maxsize=1)
def _jwks_client() -> jwt.PyJWKClient:
    """Return a cached JWKS client for the configured Cognito pool."""
    pool_id = os.environ["AREPAS_COGNITO_USER_POOL_ID"]
    region = pool_id.split("_")[0]
    url = (
        f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"
        "/.well-known/jwks.json"
    )
    return jwt.PyJWKClient(url)


def reset_auth_cache() -> None:
    """Clear JWKS client cache (tests that flip env vars between cases)."""
    _jwks_client.cache_clear()


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------

def verify_token(token: str) -> dict:
    """Decode + verify a Cognito RS256 JWT and return its claims.

    Raises :class:`jwt.PyJWTError` (or a subclass) on any failure:
    expired, bad signature, wrong issuer/audience, malformed.
    """
    pool_id = os.environ.get("AREPAS_COGNITO_USER_POOL_ID", "")
    client_id = os.environ.get("AREPAS_COGNITO_CLIENT_ID", "")
    region = pool_id.split("_")[0]
    issuer = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}"

    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["RS256"],
        audience=client_id,
        issuer=issuer,
    )


def role_from_claims(claims: dict) -> Role:
    """Map ``cognito:groups`` claim → :class:`Role`.

    ``admin`` group → admin; ``user`` group → user; no group / missing → guest.
    """
    groups: list[str] = claims.get("cognito:groups") or []
    if "admin" in groups:
        return Role.ADMIN
    if "user" in groups:
        return Role.USER
    return Role.GUEST


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------

_bearer = HTTPBearer(auto_error=False)


async def _resolve_role(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Role:
    if auth_mode() == "disabled":
        return Role.ADMIN  # local dev / no Cognito config → full access

    if credentials is None:
        return Role.GUEST

    try:
        claims = verify_token(credentials.credentials)
        return role_from_claims(claims)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token.")


async def require_guest(role: Role = Depends(_resolve_role)) -> Role:
    """Dependency: guest or above (anonymous allowed)."""
    return role


async def require_user(role: Role = Depends(_resolve_role)) -> Role:
    """Dependency: user or above (login required)."""
    if role < Role.USER:
        raise HTTPException(
            status_code=403,
            detail="Explore access requires a user account.",
        )
    return role


async def require_admin(role: Role = Depends(_resolve_role)) -> Role:
    """Dependency: admin only."""
    if role < Role.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )
    return role
