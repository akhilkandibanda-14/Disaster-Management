"""
SafeMap AI — Role-Based Access Control & Security Safeguards

Provides authentication and role-based permissions:
- Public Users: Can access permitted flood telemetry, hazard zones, risk maps, and evacuation routes.
- Analysts: Can review data manifests, validate institutional intake payloads (dry-run), inspect source catalogues, and view intake audit logs.
- Administrators: Can commit institutional dataset batches, promote or verify facility records, and manage system resources.

Supports API key authentication via:
1. `X-API-Key: <key>` header
2. `Authorization: Bearer <key>` header
"""

import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

# Optional bearer scheme that does not auto-error, allowing X-API-Key fallback
bearer_scheme = HTTPBearer(auto_error=False)


def extract_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key", description="SafeMap AI API Key"),
    bearer_auth: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    """
    Extracts the API key from either the X-API-Key header or Bearer authorization token.
    """
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if bearer_auth and bearer_auth.credentials:
        return bearer_auth.credentials.strip()
    return None


def get_current_user_role(api_key: Optional[str] = Depends(extract_api_key)) -> str:
    """
    Validates the provided API key and returns the user's role ("admin" or "analyst").
    Uses constant-time secrets.compare_digest to prevent timing side-channel attacks.
    Raises HTTP 401 Unauthorized if the key is missing or invalid.
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Provide an API key via 'X-API-Key' header or 'Authorization: Bearer <key>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate against configured admin key
    if settings.admin_api_key and secrets.compare_digest(api_key, settings.admin_api_key):
        return "admin"

    # Validate against configured analyst key
    if settings.analyst_api_key and secrets.compare_digest(api_key, settings.analyst_api_key):
        return "analyst"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed: Invalid API key credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_admin(role: str = Depends(get_current_user_role)) -> str:
    """
    Strict dependency requiring the administrator role.
    Used for sensitive state changes: committing institutional data and promoting unverified records.
    Raises HTTP 403 Forbidden if user possesses analyst privileges but lacks administrative rights.
    """
    if role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Administrative privileges are required to perform this action.",
        )
    return "admin"


def require_analyst_or_admin(api_key: Optional[str] = Depends(extract_api_key)) -> str:
    """
    Dependency requiring Analyst or Administrator privileges.
    In production environments, credentials are strictly required.
    In local development/test modes without credentials, allows default analyst inspection
    to preserve testing ergonomics while strictly rejecting invalid credentials.
    """
    if api_key:
        if settings.admin_api_key and secrets.compare_digest(api_key, settings.admin_api_key):
            return "admin"
        if settings.analyst_api_key and secrets.compare_digest(api_key, settings.analyst_api_key):
            return "analyst"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Invalid API key credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In production/staging, API keys are mandatory for all intake and administrative surfaces
    if settings.is_production() or settings.app_env.lower() in ("production", "prod", "staging"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Institutional data inspection requires an Analyst or Admin API key in production.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # In development mode, allow non-destructive inspection fallback
    return "analyst"


def get_optional_user_role(api_key: Optional[str] = Depends(extract_api_key)) -> Optional[str]:
    """
    Optional authentication for endpoints that provide additional administrative context
    when credentials are provided, but remain accessible publicly.
    """
    if not api_key:
        return None

    if settings.admin_api_key and secrets.compare_digest(api_key, settings.admin_api_key):
        return "admin"
    if settings.analyst_api_key and secrets.compare_digest(api_key, settings.analyst_api_key):
        return "analyst"

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication failed: Invalid API key credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
