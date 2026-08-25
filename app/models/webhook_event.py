import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.business import Business


class WebhookEvent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model logging incoming raw webhook payloads for auditing and asynchronous processing."""

    __tablename__ = "webhook_events"

    provider: Mapped[str] = mapped_column(String(50), default="whatsapp", nullable=False)  # whatsapp, telegram, etc.
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)  # message, delivery_status, etc.
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    business_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    business: Mapped["Business | None"] = relationship()
