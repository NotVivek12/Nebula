import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.memory import AIMemoryService
from app.ai.rag import AIRagService
from app.core.logging import logger
from app.models.agent import Agent
from app.models.business import Business
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.llm.dispatcher import get_llm_provider


class AIOrchestrator:
    """Orchestrator implementing the complete prompt, memory, RAG, and LLM call pipeline."""

    async def process_message(
        self,
        business_id: uuid.UUID,
        conversation_id: uuid.UUID,
        user_message: str,
        db: AsyncSession,
    ) -> str:
        """Runs the complete AI conversational response generation pipeline.

        Loads tenant details, builds prompt contexts, queries knowledge, calls the LLM,
        and persists the generated response.
        """
        logger.info("AI processing initiated", conversation_id=str(conversation_id))

        # 1. Load active conversation, contact, and business
        conv_query = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
            .where(Conversation.business_id == business_id)
            .options(selectinload(Conversation.contact))
        )
        res = await db.execute(conv_query)
        conversation = res.scalar_one_or_none()

        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found for business {business_id}")

        contact = conversation.contact
        business = await db.get(Business, business_id)
        if not business:
            raise ValueError(f"Business {business_id} not found")

        # 2. Load active agent config (fallback to a system default if not configured)
        agent_query = select(Agent).where(Agent.business_id == business_id).limit(1)
        res = await db.execute(agent_query)
        agent = res.scalar_one_or_none()

        if not agent:
            # Fallback configuration
            agent = Agent(
                name="Default Support Agent",
                system_prompt="You are a helpful customer support assistant for Nebula.",
                provider="openai",
                model_name="gpt-4o",
                temperature=0.7,
                business_id=business_id,
            )

        # 3. Retrieve Customer Long-Term Memories/Preferences
        memory_service = AIMemoryService(db)
        memories = await memory_service.retrieve_memories(
            contact_id=contact.id,
            business_id=business_id,
            query_text=user_message,
            limit=5,
        )

        # 4. Load Short-term Memory (Last 15 messages)
        history_query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(15)
        )
        res = await db.execute(history_query)
        db_messages = list(res.scalars().all())
        db_messages.reverse()  # Sort chronologically

        conversation_history = []
        for msg in db_messages:
            # incoming customer messages are "user", outgoing are "assistant"
            role = "user" if msg.sender_type == "contact" else "assistant"
            # Prevent sending structural JSON templates or media filepaths as raw prompt contexts
            if msg.content.strip().startswith("{") and msg.content.strip().endswith("}"):
                continue
            conversation_history.append({"role": role, "content": msg.content})

        # 5. Load Knowledge (RAG)
        rag_service = AIRagService(db, business_id)
        knowledge_chunks = await rag_service.query_knowledge(user_message, limit=3)

        # 6. Build prompt context
        system_prompt = agent.system_prompt or "You are a helpful assistant."

        # Inject Tenant Context
        context_headers = [
            f"Business Name: {business.name}",
            f"Customer Name: {contact.name or 'Unknown'}",
            f"Customer Phone: {contact.phone_number}",
            f"Current UTC Time: {datetime.now(timezone.utc).isoformat()}",
        ]
        system_prompt += "\n\n[Active Session Metadata]\n" + "\n".join(context_headers)

        # Inject Retrieved Long-Term Memories
        if memories:
            memory_lines = [f"- [Type: {m.memory_type}] {m.content}" for m in memories]
            system_prompt += "\n\n[Retrieved Customer Long-Term Memories/Preferences]\n" + "\n".join(memory_lines)

        # Inject Knowledge context
        if knowledge_chunks:
            system_prompt += (
                "\n\n[Context Knowledge Base Chunks]\n"
                + "\n---\n".join(knowledge_chunks)
                + "\n---\nUse the knowledge chunks to answer accurately."
            )

        # 7. Call active LLM Provider
        provider = await get_llm_provider(business_id, agent.provider, db)
        reply = await provider.generate_response(
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            user_message=user_message,
            model_name=agent.model_name,
            temperature=agent.temperature,
        )

        # 8. Persist generated response to DB
        agent_message = Message(
            sender_type="agent",
            content=reply,
            status="sent",
            conversation_id=conversation_id,
        )
        db.add(agent_message)

        # Update contact last interaction time
        contact.last_interaction = datetime.now(timezone.utc)
        db.add(contact)

        await db.commit()
        logger.info("AI response generated and persisted", message_id=str(agent_message.id))

        # 9. Perform background memory management updates
        try:
            # Check for summarization (adds summary facts) and pruning/consolidation
            await memory_service.summarize_conversation(conversation_id, provider, agent.model_name)
            await memory_service.prune_memories(contact.id, business_id, provider, agent.model_name)
        except Exception as e:
            logger.warn("Background memory manager updates failed", error=str(e))

        return reply
