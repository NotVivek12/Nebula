import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagBase(BaseModel):
    name: str


class TagCreate(TagBase):
    pass


class TagResponse(TagBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID


class ConversationBase(BaseModel):
    status: str = "active"
    custom_metadata: dict | None = None


class ConversationCreate(BaseModel):
    """Schema to open a new conversation thread."""

    contact_id: uuid.UUID


class ConversationUpdate(BaseModel):
    status: str | None = None
    custom_metadata: dict | None = None


class ConversationResponse(ConversationBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unread_count: int
    contact_id: uuid.UUID
    business_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    tags: list[TagResponse] = []


class StatusAssignRequest(BaseModel):
    """Request schema to assign a lifecycle state status."""

    status: str  # active, closed, archived, escalated


class TagsAssignRequest(BaseModel):
    """Request schema to assign a list of tag names to a conversation."""

    tags: list[str]
