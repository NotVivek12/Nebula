import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.business import Business
    from app.models.role import Role
    from app.models.user import User


class UserInvitation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model tracking pending and accepted invitations for team membership onboarding."""

    __tablename__ = "user_invitations"

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending, accepted, expired
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    invited_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="invitations")
    invited_by: Mapped["User | None"] = relationship(back_populates="invitations_sent")
    role: Mapped["Role"] = relationship()
