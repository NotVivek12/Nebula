import uuid

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.business_user import BusinessUser
from app.models.role import Role
from app.models.user import User


async def get_current_business_id(
    x_business_id: str = Header(..., alias="X-Business-ID"),
) -> uuid.UUID:
    """Extracts and validates the active tenant business ID from request headers."""
    try:
        return uuid.UUID(x_business_id)
    except ValueError:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Business-ID header must be a valid UUID",
        )


async def get_current_membership(
    current_user: User = Depends(get_current_user),
    business_id: uuid.UUID = Depends(get_current_business_id),
    db: AsyncSession = Depends(get_db),
) -> BusinessUser:
    """Verifies that the authenticated user belongs to the active tenant business.

    Eagerly loads the associated Role and Permission sets.
    """
    query = (
        select(BusinessUser)
        .where(BusinessUser.user_id == current_user.id)
        .where(BusinessUser.business_id == business_id)
        .options(selectinload(BusinessUser.role).selectinload(Role.permissions))
    )
    result = await db.execute(query)
    membership = result.scalar_one_or_none()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not a member of this business tenant",
        )

    return membership


class RequirePermission:
    """Dynamic FastAPI dependency guarding actions against a granular action permission key."""

    def __init__(self, permission_name: str) -> None:
        self.permission_name = permission_name

    async def __call__(
        self,
        membership: BusinessUser = Depends(get_current_membership),
    ) -> BusinessUser:
        """Verifies active membership contains the required permission name."""
        permissions = {p.name for p in membership.role.permissions}
        if self.permission_name not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: '{self.permission_name}'",
            )
        return membership


class RequireRole:
    """Dynamic FastAPI dependency guarding actions against a broad role identifier (e.g., Owner)."""

    def __init__(self, role_name: str) -> None:
        self.role_name = role_name

    async def __call__(
        self,
        membership: BusinessUser = Depends(get_current_membership),
    ) -> BusinessUser:
        """Verifies active membership role matches target role name."""
        if membership.role.name != self.role_name:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required role: '{self.role_name}'",
            )
        return membership
