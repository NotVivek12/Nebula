import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class InvitationCreate(BaseModel):
    """Schema for inviting a new user to a business tenant."""

    email: EmailStr
    role_id: uuid.UUID


class InvitationAccept(BaseModel):
    """Schema for accepting a tenant business invitation."""

    token: str
    password: str
    full_name: str | None = None


class InvitationResponse(BaseModel):
    """Schema for invitation detail responses."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    status: str
    business_id: uuid.UUID
    role_id: uuid.UUID
    expires_at: datetime
