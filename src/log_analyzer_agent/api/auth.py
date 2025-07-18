"""Authentication dependencies for FastAPI."""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..services.auth_service import AuthService
from .models import UserResponse


security = HTTPBearer()


def get_auth_service() -> AuthService:
    """Get authentication service instance."""
    import os

    db_url = os.getenv(
        "DATABASE_URL", "postgresql://loganalyzer:password@localhost:5432/loganalyzer"
    )
    return AuthService(db_url)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Get current authenticated user."""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        user_data = await auth_service.verify_session(credentials.credentials)
        if user_data is None:
            raise credentials_exception

        return UserResponse(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data.get("full_name"),
            is_active=True,
            created_at="",  # We'll fill this in if needed
        )
    except Exception:
        raise credentials_exception


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[UserResponse]:
    """Get current authenticated user (optional)."""

    if not credentials:
        return None

    try:
        user_data = await auth_service.verify_session(credentials.credentials)
        if user_data is None:
            return None

        return UserResponse(
            id=user_data["id"],
            email=user_data["email"],
            full_name=user_data.get("full_name"),
            is_active=True,
            created_at="",
        )
    except Exception:
        return None
