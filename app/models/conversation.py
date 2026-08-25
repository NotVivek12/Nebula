import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.contact import Contact
    from app.models.message import Message
    from app.models.tag import Tag
    from app.models.user import User


class Conversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing an ongoing or historical conversation thread."""

    __tablename__ = "conversations"

    status: Mapped[str] = mapped_column(
        String(50), default="active", nullable=False
    )  # active, closed, archived, escalated
    unread_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    custom_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_ai_controlled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    active_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )

    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False
    )
    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    contact: Mapped["Contact"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="conversation_tags", back_populates="conversations"
    )
    assigned_agent: Mapped["User | None"] = relationship()
    active_agent: Mapped["Agent | None"] = relationship()
