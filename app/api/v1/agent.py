import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import RequirePermission
from app.db.session import get_db
from app.models.agent import Agent, AgentAnalytics
from app.models.business_user import BusinessUser
from app.schemas.agent import (
    AgentAnalyticsResponse,
    AgentCreate,
    AgentHandoffRequest,
    AgentResponse,
)
from app.services.agent.orchestrator import MultiAgentOrchestrator

router = APIRouter()


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    payload: AgentCreate,
    membership: BusinessUser = Depends(RequirePermission("agents:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Configures a new AI agent for the business fleet (requires agents:write permission)."""
    # Verify that agent role is within standard limits
    valid_roles = ["sales", "support", "marketing", "billing", "operations"]
    if payload.role.lower() not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid agent role. Must be one of: {valid_roles}",
        )

    agent = Agent(
        name=payload.name,
        role=payload.role.lower(),
        instructions=payload.instructions,
        system_prompt=payload.system_prompt,
        provider=payload.provider,
        model_name=payload.model_name,
        temperature=payload.temperature,
        tools=payload.tools,
        permissions=payload.permissions,
        business_id=membership.business_id,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # Initialize analytics row
    analytics = AgentAnalytics(
        agent_id=agent.id,
        run_count=0,
        success_count=0,
        total_latency=0.0,
    )
    db.add(analytics)
    await db.commit()

    return agent


@router.get("", response_model=list[AgentResponse])
async def list_agents(
    membership: BusinessUser = Depends(RequirePermission("agents:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Lists all AI agent definitions configured for the business (requires agents:read permission)."""
    query = select(Agent).where(Agent.business_id == membership.business_id)
    res = await db.execute(query)
    return res.scalars().all()


@router.post("/handoff", response_model=dict[str, Any])
async def manual_agent_handoff(
    conversation_id: uuid.UUID,
    payload: AgentHandoffRequest,
    membership: BusinessUser = Depends(RequirePermission("agents:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Manually hands off a conversation thread to a different AI agent (requires agents:write)."""
    # Fetch active agent configurations
    agent_query = select(Agent).where(Agent.business_id == membership.business_id)
    res = await db.execute(agent_query)
    agents = {a.id: a for a in res.scalars().all()}

    if payload.to_agent_id not in agents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Destination agent not found inside this business tenant.",
        )

    # Load conversation and verify ownership
    # Let's select Conversation directly:
    from app.models.conversation import Conversation
    query = select(Conversation).where(Conversation.id == conversation_id).where(Conversation.business_id == membership.business_id)
    res = await db.execute(query)
    conversation = res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation thread not found.",
        )

    from_agent_id = conversation.active_agent_id
    orchestrator = MultiAgentOrchestrator()
    await orchestrator.execute_handoff(
        conversation_id=conversation_id,
        from_agent_id=from_agent_id,
        to_agent_id=payload.to_agent_id,
        reason=payload.reason,
        business_id=membership.business_id,
        db=db,
    )

    return {
        "status": "success",
        "conversation_id": str(conversation_id),
        "from_agent_id": str(from_agent_id) if from_agent_id else None,
        "to_agent_id": str(payload.to_agent_id),
    }


@router.get("/{agent_id}/analytics", response_model=AgentAnalyticsResponse)
async def get_agent_analytics(
    agent_id: uuid.UUID,
    membership: BusinessUser = Depends(RequirePermission("agents:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieves execution metrics for a specific agent (requires agents:read permission)."""
    # Verify agent ownership
    query = select(Agent).where(Agent.id == agent_id).where(Agent.business_id == membership.business_id)
    res = await db.execute(query)
    agent = res.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found within this business tenant.",
        )

    analytics_query = select(AgentAnalytics).where(AgentAnalytics.agent_id == agent_id)
    res = await db.execute(analytics_query)
    analytics = res.scalar_one_or_none()

    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics metrics not initialized for this agent.",
        )

    return analytics
