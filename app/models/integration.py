import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Integration(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing an external integration configuration for a business."""

    __tablename__ = "integrations"

    provider: Mapped[str] = mapped_column(String(100), nullable=False)  # google_sheets, gmail, google_calendar, etc.
    credentials: Mapped[dict] = mapped_column(JSONB, nullable=False)  # encrypted tokens or connection credentials
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
