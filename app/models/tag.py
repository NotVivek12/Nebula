import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, String, Table, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.conversation import Conversation

# Many-to-many join table for Conversation and Tag mapping
conversation_tags = Table(
    "conversation_tags",
    Base.metadata,
    Column(
        "conversation_id",
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Tag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing custom classification tags defined by business tenants."""

    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("business_id", "name", name="uq_tag_business_name"),)

    name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    business: Mapped["Business"] = relationship()
    conversations: Mapped[list["Conversation"]] = relationship(
        secondary=conversation_tags, back_populates="tags"
    )
