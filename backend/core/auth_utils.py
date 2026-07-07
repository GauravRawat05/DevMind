"""Authentication utilities for password hashing, verification, and JWT generation."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
import jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.database import get_db
from backend.models.pg_models import User

logger = logging.getLogger("devmind.core.auth_utils")

# Security scheme
security_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the hashed password."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as exc:
        logger.error("Password verification error: %s", exc)
        return False


def create_access_token(user_id: int, email: str, expires_delta: timedelta | None = None) -> str:
    """Generate a JWT access token for a user."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=24)
        
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": expire,
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode a JWT access token. Returns payload dict or None if invalid."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("JWT Token has expired")
        return None
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT Token is invalid: %s", exc)
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User | None:
    """FastAPI dependency to retrieve the currently logged-in user from a JWT token.

    Returns None if no authorization credentials are provided (enabling optional auth).
    Raises 401 Unauthorized if credentials are provided but invalid/expired.
    """
    if not credentials:
        return None
        
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    user_id_str = payload["sub"]
    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject payload.",
        )
        
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user not found in database.",
        )
        
    return user


async def require_auth(
    user: User | None = Depends(get_current_user)
) -> User:
    """FastAPI dependency to require authentication on an endpoint.

    Raises 401 Unauthorized if the user is not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is required to access this resource.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
