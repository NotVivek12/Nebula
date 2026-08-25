from pydantic import BaseModel


class MessageSendRequest(BaseModel):
    """Request validation schema for outgoing messages."""

    recipient: str  # Destination phone number (e.g., "+1234567890")
    content: str  # Plain text, or a serialized JSON block for templates/media
