import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.conversation import Conversation


class Message(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing an incoming or outgoing message."""

    __tablename__ = "messages"

    sender_type: Mapped[str] = mapped_column(String(50), nullable=False)  # contact, agent, system, user
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="sent", nullable=False)  # sent, delivered, read, failed
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255), unique=True, index=True, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
