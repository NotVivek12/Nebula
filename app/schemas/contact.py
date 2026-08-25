import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ContactBase(BaseModel):
    phone_number: str
    name: str | None = None
    lead_status: str | None = None
    custom_metadata: dict | None = None


class ContactUpdate(BaseModel):
    """Schema to update a customer profile."""

    phone_number: str | None = None
    name: str | None = None
    lead_status: str | None = None
    custom_metadata: dict | None = None


class ContactResponse(ContactBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
