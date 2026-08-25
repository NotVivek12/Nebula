"""
FastAPI dependency providers for authenticated requests.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.user import UserRepository

# OAuth2 scheme — configures Swagger UI authorization modal
reusable_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/token"
)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(reusable_oauth2),
) -> User:
    """
    Validates JWT and returns the active authenticated user.

    Raises HTTP 401 if:
    - Token is missing, malformed, expired, or has wrong type/issuer/audience
    - User does not exist in the database
    - User account is not active (is_active == False)
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    subject = decode_access_token(token)
    if subject is None:
        raise credentials_exception

    user_repo = UserRepository(db)
    user = await user_repo.get(subject)

    if user is None:
        raise credentials_exception

    # Active account check — prevents deactivated accounts from continuing to use tokens
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    return user
