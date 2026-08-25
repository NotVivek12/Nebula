import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.conversation import Conversation


class AgentHandoff(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing an audit trace of a conversation assignment transfer between AI agents."""

    __tablename__ = "agent_handoffs"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    from_agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    to_agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=False
    )
    reason: Mapped[str] = mapped_column(String(512), nullable=False)

    # Relationships
    conversation: Mapped["Conversation"] = relationship()
    from_agent: Mapped["Agent | None"] = relationship(foreign_keys=[from_agent_id])
    to_agent: Mapped["Agent"] = relationship(foreign_keys=[to_agent_id])
