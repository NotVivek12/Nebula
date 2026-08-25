import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import RequirePermission
from app.db.session import get_db
from app.models.business_user import BusinessUser
from app.repositories.contact import ContactRepository
from app.schemas.contact import ContactResponse, ContactUpdate

router = APIRouter()


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: uuid.UUID,
    membership: BusinessUser = Depends(RequirePermission("contacts:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieves specific customer contact profiles (requires contacts:read permission)."""
    repo = ContactRepository(db)
    contact = await repo.get(contact_id)

    if not contact or contact.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found within this business tenant.",
        )

    return contact


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: uuid.UUID,
    payload: ContactUpdate,
    membership: BusinessUser = Depends(RequirePermission("contacts:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Updates customer contact profile fields (requires contacts:write permission)."""
    repo = ContactRepository(db)
    contact = await repo.get(contact_id)

    if not contact or contact.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found within this business tenant.",
        )

    # Filter out None values to perform partial updates
    update_data = payload.model_dump(exclude_unset=True)
    updated = await repo.update(contact, update_data)
    return updated
