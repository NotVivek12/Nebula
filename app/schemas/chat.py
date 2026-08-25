import uuid

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    """Request validation schema for interactive AI chat processing."""

    conversation_id: uuid.UUID
    message: str
