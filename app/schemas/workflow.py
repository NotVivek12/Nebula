import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class WorkflowBase(BaseModel):
    name: str
    trigger_type: str
    definition: dict
    is_active: bool = True


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowResponse(WorkflowBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class WorkflowRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    current_node_id: str | None = None
    context_state: dict
    workflow_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class WorkflowNodeLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    node_id: str
    node_type: str
    status: str
    input_data: dict | None = None
    output_data: dict | None = None
    error_message: str | None = None
    execution_time: float
    created_at: datetime


class WorkflowApproveRequest(BaseModel):
    """Request schema to approve a paused human approval node."""

    decision: str  # approve, deny
    notes: str | None = None
