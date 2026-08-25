import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentBase(BaseModel):
    name: str
    role: str
    instructions: str
    system_prompt: str | None = None
    provider: str = "openai"
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    tools: list[str] = []
    permissions: list[str] = []


class AgentCreate(AgentBase):
    pass


class AgentResponse(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class AgentHandoffRequest(BaseModel):
    """Request schema to manually route/hand off a conversation thread to another agent."""

    to_agent_id: uuid.UUID
    reason: str


class AgentHandoffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    from_agent_id: uuid.UUID | None = None
    to_agent_id: uuid.UUID
    reason: str
    created_at: datetime


class AgentAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: uuid.UUID
    run_count: int
    success_count: int
    total_latency: float
