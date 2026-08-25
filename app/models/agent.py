import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.business import Business


class Agent(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing an AI Agent configuration for a business."""

    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)  # sales, support, marketing, billing, operations
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="openai", nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="gpt-4o", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.7, nullable=False)

    # Configured tools list (e.g. ["create_lead", "send_email"])
    tools: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    # Required permissions to execute tools (e.g. ["contacts:write"])
    permissions: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    business: Mapped["Business"] = relationship(back_populates="agents")
    analytics: Mapped["AgentAnalytics"] = relationship(
        back_populates="agent", uselist=False, cascade="all, delete-orphan"
    )


class AgentAnalytics(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model tracking AI Agent execution metrics, successes, and latencies."""

    __tablename__ = "agent_analytics"

    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_latency: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    agent: Mapped["Agent"] = relationship(back_populates="analytics")
