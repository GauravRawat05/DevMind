"""FastAPI router for user authentication and user job profiles."""

from __future__ import annotations

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.auth_utils import hash_password, verify_password, create_access_token, require_auth
from backend.models.pg_models import User, Job

logger = logging.getLogger("devmind.api.auth")

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserRegisterRequest(BaseModel):
    """Schema for user registration request."""

    email: EmailStr = Field(..., description="Unique email address for user registration")
    password: str = Field(..., min_length=6, description="Password (min 6 characters)")


class UserLoginRequest(BaseModel):
    """Schema for user login request."""

    email: EmailStr = Field(..., description="User's email address")
    password: str = Field(..., description="User's password")


class AuthTokenResponse(BaseModel):
    """Response returned upon successful authentication (login/register)."""

    access_token: str
    token_type: str = "bearer"
    email: str


class UserProfileResponse(BaseModel):
    """Schema for returning user profile details."""

    id: int
    email: str
    created_at: str


class UserJobSummary(BaseModel):
    """Schema summarizing a job in user history."""

    job_id: str
    repo_url: str
    status: str
    created_at: str
    updated_at: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
async def register_user(
    body: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Creates a new user profile with hashed password, returning a JWT token."""
    email = body.email.lower().strip()
    
    # Check if user already exists
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )
        
    # Create user
    hashed = hash_password(body.password)
    user = User(email=email, hashed_password=hashed)
    db.add(user)
    
    try:
        await db.commit()
        await db.refresh(user)
        logger.info("Successfully registered new user: %s (id=%d)", email, user.id)
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to commit new user to PG database: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database registration transaction failed."
        )
        
    # Generate token
    token = create_access_token(user.id, user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email
    }


@router.post(
    "/login",
    response_model=AuthTokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login to an existing user account"
)
async def login_user(
    body: UserLoginRequest,
    db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """Authenticates credentials and returns a JWT access token."""
    email = body.email.lower().strip()
    
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    logger.info("User logged in successfully: %s", email)
    token = create_access_token(user.id, user.email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email
    }


@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get authenticated user profile information"
)
async def get_user_profile(
    current_user: User = Depends(require_auth)
) -> dict[str, Any]:
    """Returns profile details of the authenticated requester."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "created_at": current_user.created_at.isoformat()
    }


@router.get(
    "/me/jobs",
    response_model=list[UserJobSummary],
    status_code=status.HTTP_200_OK,
    summary="Retrieve all repository analysis jobs for the logged-in user"
)
async def get_user_jobs(
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
) -> list[dict[str, Any]]:
    """Lists all past and present jobs associated with the authenticated user's account."""
    stmt = select(Job).where(Job.user_id == current_user.id).order_by(Job.created_at.desc())
    result = await db.execute(stmt)
    jobs = result.scalars().all()
    
    return [
        {
            "job_id": job.id,
            "repo_url": job.repo_url,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat()
        }
        for job in jobs
    ]
