import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.contact_memory import ContactMemory
    from app.models.conversation import Conversation


class Contact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing a customer contact."""

    __tablename__ = "contacts"

    phone_number: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lead_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    last_interaction: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    custom_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="contacts")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )
    memories: Mapped[list["ContactMemory"]] = relationship(
        back_populates="contact", cascade="all, delete-orphan"
    )
