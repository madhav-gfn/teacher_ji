"""
Clerk session-token verification.

Clerk issues RS256 JWTs whose public signing keys are published at the
instance's JWKS endpoint, so verification needs no secret key — just the
issuer (frontend API) URL, derived once from CLERK_ISSUER.

The Clerk user id (the JWT's `sub` claim) is used directly as students.student_id
and documents.student_id — there is no separate mapping table.
"""
from __future__ import annotations

import logging
import os

import jwt
from fastapi import Header, HTTPException
from jwt import PyJWKClient

logger = logging.getLogger(__name__)

_CLERK_ISSUER = os.getenv("CLERK_ISSUER", "").rstrip("/")
_jwks_client = PyJWKClient(f"{_CLERK_ISSUER}/.well-known/jwks.json") if _CLERK_ISSUER else None


async def get_current_student_id(authorization: str | None = Header(default=None)) -> str:
    """FastAPI dependency: verify the bearer JWT and return the Clerk user id."""
    if _jwks_client is None:
        raise HTTPException(status_code=500, detail="Auth is not configured (CLERK_ISSUER unset).")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=_CLERK_ISSUER,
            options={"verify_aud": False},
            # Clerk session tokens have a ~60s validity window by design, so
            # even a few seconds of container clock drift is enough to reject
            # a genuinely valid token. Tolerate some skew rather than trusting
            # the host clock to be perfectly synced.
            leeway=60,
        )
    except jwt.PyJWTError as exc:
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired session token.") from exc

    student_id = claims.get("sub")
    if not student_id:
        raise HTTPException(status_code=401, detail="Token missing subject claim.")
    return student_id


def require_owner(resource_student_id: str, current_student_id: str) -> None:
    """Raise 403 unless the authenticated user owns this resource."""
    if resource_student_id != current_student_id:
        raise HTTPException(status_code=403, detail="You do not have access to this resource.")
