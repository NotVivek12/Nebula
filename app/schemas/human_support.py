import uuid

from pydantic import BaseModel


class ConversationAssignRequest(BaseModel):
    """Request schema to assign a conversation to an agent user."""

    assigned_agent_id: uuid.UUID | None = None


class InternalCommentCreate(BaseModel):
    """Request schema to add an internal comment note to a conversation."""

    content: str


class TypingIndicatorRequest(BaseModel):
    """Request schema to trigger an agent typing indicator status broadcast."""

    is_typing: bool
