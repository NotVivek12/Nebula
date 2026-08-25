import uuid

from sqlalchemy import Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Workflow(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing an automation workflow definition."""

    __tablename__ = "workflows"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    trigger_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # message_received, form_submitted, manual, etc.
    definition: Mapped[dict] = mapped_column(JSONB, nullable=False)  # JSON graph structure
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    runs: Mapped[list["WorkflowRun"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing an execution instance of a workflow."""

    __tablename__ = "workflow_runs"

    status: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False
    )  # pending, running, completed, failed, paused
    logs: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # legacy log object
    current_node_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    context_state: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)  # variable stack

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    workflow: Mapped["Workflow"] = relationship(back_populates="runs")
    node_logs: Mapped[list["WorkflowNodeLog"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class WorkflowNodeLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing a detailed execution log entry for a specific workflow node."""

    __tablename__ = "workflow_node_logs"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(String(100), nullable=False)
    node_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # success, failed, retrying, paused
    input_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    execution_time: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    run: Mapped["WorkflowRun"] = relationship(back_populates="node_logs")
