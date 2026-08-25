import time
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.tools.registry import ToolRegistry
from app.core.logging import logger
from app.models.agent import Agent, AgentAnalytics
from app.models.agent_handoff import AgentHandoff
from app.models.conversation import Conversation
from app.services.llm.dispatcher import get_llm_provider
from app.services.websocket_manager import manager


class MultiAgentOrchestrator:
    """Orchestrates routing, intent selection, handoffs, and execution of multi-agent conversations."""

    async def select_agent(
        self,
        business_id: uuid.UUID,
        message_text: str,
        active_agent_id: uuid.UUID | None,
        db: AsyncSession,
    ) -> Agent | None:
        """Classifies incoming query intent to select the most appropriate AI agent from the business's fleet."""
        # 1. Fetch all configured agents for this business
        query = select(Agent).where(Agent.business_id == business_id).options(selectinload(Agent.analytics))
        res = await db.execute(query)
        agents = list(res.scalars().all())

        if not agents:
            return None

        if len(agents) == 1:
            return agents[0]

        # 2. Run LLM intent selection step
        # Default to first active agent config details
        active_agent = next((a for a in agents if a.id == active_agent_id), agents[0])
        provider = await get_llm_provider(business_id, active_agent.provider, db)

        agent_options = "\n".join(
            [f"- ID: {a.id} | Name: {a.name} | Role: {a.role}\n  Instructions: {a.instructions[:150]}" for a in agents]
        )

        system_prompt = (
            "You are a routing agent for a multi-agent system. Review the available agents list below:\n"
            f"{agent_options}\n\n"
            "Based on the customer's message, select the best agent suited to handle the request.\n"
            "Return strictly the selected Agent ID UUID and absolutely nothing else."
        )

        try:
            llm_reply = await provider.generate_response(
                system_prompt=system_prompt,
                conversation_history=[],
                user_message=message_text,
                model_name=active_agent.model_name,
                temperature=0.0,
            )
            selected_id_str = llm_reply.strip()
            selected_uuid = uuid.UUID(selected_id_str)
            matched = next((a for a in agents if a.id == selected_uuid), None)
            if matched:
                return matched
        except Exception as e:
            logger.warn("Selector fallback triggered during multi-agent classification", error=str(e))

        # Fallback to current agent or first agent
        return next((a for a in agents if a.id == active_agent_id), agents[0])

    async def execute_handoff(
        self,
        conversation_id: uuid.UUID,
        from_agent_id: uuid.UUID | None,
        to_agent_id: uuid.UUID,
        reason: str,
        business_id: uuid.UUID,
        db: AsyncSession,
    ) -> None:
        """Executes the handoff mapping: logs the Handoff audit record and updates conversation pointer."""
        handoff = AgentHandoff(
            conversation_id=conversation_id,
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            reason=reason,
        )
        db.add(handoff)

        # Update Conversation pointer
        query = select(Conversation).where(Conversation.id == conversation_id)
        res = await db.execute(query)
        conversation = res.scalar_one()
        conversation.active_agent_id = to_agent_id
        db.add(conversation)

        await db.commit()

        logger.info(
            "AI Agent handoff executed",
            conversation_id=str(conversation_id),
            from_agent=str(from_agent_id) if from_agent_id else "None",
            to_agent=str(to_agent_id),
        )

        # Broadcast live WebSockets update
        await manager.broadcast_to_tenant(
            business_id,
            {
                "event": "agent_handoff",
                "conversation_id": str(conversation_id),
                "from_agent_id": str(from_agent_id) if from_agent_id else None,
                "to_agent_id": str(to_agent_id),
                "reason": reason,
            },
        )

    async def route_and_respond(
        self,
        conversation_id: uuid.UUID,
        user_message: str,
        db: AsyncSession,
    ) -> str:
        """Determines active agent, runs selection intent router, handles handoffs, and executes pipeline."""
        start_time = time.time()

        # Load conversation
        query = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .options(selectinload(Conversation.active_agent))
        )
        res = await db.execute(query)
        conversation = res.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found.")

        business_id = conversation.business_id
        current_agent = conversation.active_agent

        # 1. Resolve current or newly routed agent
        selected_agent = await self.select_agent(
            business_id=business_id,
            message_text=user_message,
            active_agent_id=conversation.active_agent_id,
            db=db,
        )

        if not selected_agent:
            return "No agents are configured for this business tenant. Please register an agent first."

        # Execute handoff if intent maps to a different agent role
        if not current_agent or current_agent.id != selected_agent.id:
            await self.execute_handoff(
                conversation_id=conversation_id,
                from_agent_id=conversation.active_agent_id,
                to_agent_id=selected_agent.id,
                reason="Automatic routing classification match based on customer intent.",
                business_id=business_id,
                db=db,
            )
            # Reload agent pointer
            current_agent = selected_agent

        # 2. Execute selected agent response generation
        provider = await get_llm_provider(business_id, current_agent.provider, db)

        system_prompt = (
            f"You are the {current_agent.name} AI Agent, operating in the role of {current_agent.role}.\n"
            f"Instructions:\n{current_agent.instructions}\n\n"
            f"Business System Context: Ensure your replies are helpful and aligned with the instructions."
        )

        # Generate response using restricted tools set matching config
        # Verify/limit the agent's function calls to `current_agent.tools`
        # For this setup, the prompt will list available tools from registry that match agent.tools list
        registry = ToolRegistry()
        available_tools = []
        for tname in current_agent.tools:
            tool = registry.get_tool(tname)
            if tool:
                available_tools.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    }
                )

        if available_tools:
            system_prompt += f"\n\nAvailable Tools:\n{available_tools}\nTo invoke a tool, call it."

        try:
            # Dispatch to LLM
            reply = await provider.generate_response(
                system_prompt=system_prompt,
                conversation_history=[],  # History can be injected via message logs
                user_message=user_message,
                model_name=current_agent.model_name,
                temperature=current_agent.temperature,
            )

            # Update Agent performance analytics
            latency = time.time() - start_time
            await self._update_analytics(current_agent.id, latency, success=True, db=db)
            return reply

        except Exception as e:
            logger.error("Agent execution failed", agent_id=str(current_agent.id), error=str(e))
            latency = time.time() - start_time
            await self._update_analytics(current_agent.id, latency, success=False, db=db)
            raise

    async def _update_analytics(
        self,
        agent_id: uuid.UUID,
        latency: float,
        success: bool,
        db: AsyncSession,
    ) -> None:
        """Helper to increment execution counters, success states, and latencies inside DB."""
        # Select agent analytics
        query = select(AgentAnalytics).where(AgentAnalytics.agent_id == agent_id)
        res = await db.execute(query)
        analytics = res.scalar_one_or_none()

        if not analytics:
            analytics = AgentAnalytics(
                agent_id=agent_id,
                run_count=0,
                success_count=0,
                total_latency=0.0,
            )
            db.add(analytics)

        analytics.run_count += 1
        if success:
            analytics.success_count += 1
        analytics.total_latency += latency

        db.add(analytics)
        await db.commit()
