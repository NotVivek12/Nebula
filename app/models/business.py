from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.business_user import BusinessUser
    from app.models.contact import Contact
    from app.models.invitation import UserInvitation
    from app.models.role import Role


class Business(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing a Business tenant in the platform."""

    __tablename__ = "businesses"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Relationships
    memberships: Mapped[list["BusinessUser"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    contacts: Mapped[list["Contact"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    invitations: Mapped[list["UserInvitation"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
    roles: Mapped[list["Role"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )
