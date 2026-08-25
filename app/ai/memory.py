import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.contact_memory import ContactMemory
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.llm.base import BaseLLMProvider


class AIMemoryService:
    """Manages long-term customer memory storage, semantic keyword ranking, summarization, and pruning."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def add_memory(
        self,
        contact_id: uuid.UUID,
        business_id: uuid.UUID,
        content: str,
        memory_type: str = "fact",
        relevance_score: float = 1.0,
    ) -> ContactMemory:
        """Stores a new customer fact or preference context."""
        memory = ContactMemory(
            contact_id=contact_id,
            business_id=business_id,
            memory_type=memory_type,
            content=content,
            relevance_score=relevance_score,
            last_accessed_at=datetime.now(timezone.utc),
        )
        self.db.add(memory)
        await self.db.commit()
        logger.info(
            "Saved customer memory record",
            contact_id=str(contact_id),
            type=memory_type,
        )
        return memory

    async def retrieve_memories(
        self,
        contact_id: uuid.UUID,
        business_id: uuid.UUID,
        query_text: str,
        limit: int = 5,
    ) -> list[ContactMemory]:
        """Retrieves and ranks customer memories matching query terms using keyword intersection scoring."""
        query = (
            select(ContactMemory)
            .where(ContactMemory.contact_id == contact_id)
            .where(ContactMemory.business_id == business_id)
            .where(ContactMemory.is_active.is_(True))
        )
        res = await self.db.execute(query)
        memories = list(res.scalars().all())

        # Update last accessed timestamps
        for m in memories:
            m.last_accessed_at = datetime.now(timezone.utc)
            self.db.add(m)
        await self.db.flush()

        # Simple Python keyword ranking fallback (extremely fast and robust for list sizes under 100)
        query_words = set(query_text.lower().strip().split())
        if not query_words:
            # Order by latest created if query is empty
            memories.sort(key=lambda x: x.created_at, reverse=True)
            return memories[:limit]

        ranked_memories = []
        for memory in memories:
            content_words = set(memory.content.lower().split())
            intersection = query_words.intersection(content_words)
            # Rank score = match overlap count * relevance multiplier
            score = len(intersection) * memory.relevance_score
            ranked_memories.append((score, memory))

        # Sort descending by score, then descending by recency
        ranked_memories.sort(key=lambda x: (x[0], x[1].created_at), reverse=True)

        return [item[1] for item in ranked_memories[:limit]]

    async def summarize_conversation(
        self,
        conversation_id: uuid.UUID,
        provider: BaseLLMProvider,
        model_name: str,
        temperature: float = 0.5,
    ) -> str | None:
        """Asynchronously summarizes long active conversation logs using LLM prompts."""
        # Load conversation and history logs
        conv_query = select(Conversation).where(Conversation.id == conversation_id)
        res = await self.db.execute(conv_query)
        conversation = res.scalar_one_or_none()

        if not conversation:
            return None

        # Fetch messages
        msg_query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        res = await self.db.execute(msg_query)
        messages = res.scalars().all()

        if len(messages) < 6:
            # Skip if there's insufficient history to warrant a summary
            return None

        history_lines = []
        for m in messages:
            speaker = "Customer" if m.sender_type == "contact" else "Agent"
            if m.content.strip().startswith("{") and m.content.strip().endswith("}"):
                continue
            history_lines.append(f"{speaker}: {m.content}")

        history_text = "\n".join(history_lines)
        system_prompt = (
            "You are a conversation summarizer. Summarize the following customer chat history "
            "in one brief, concise sentence outlining the primary issue discussed and any open actions."
        )

        try:
            summary = await provider.generate_response(
                system_prompt=system_prompt,
                conversation_history=[],
                user_message=f"Chat History:\n{history_text}",
                model_name=model_name,
                temperature=temperature,
            )

            # Store the generated summary as a summary type memory entry
            await self.add_memory(
                contact_id=conversation.contact_id,
                business_id=conversation.business_id,
                content=summary.strip(),
                memory_type="summary",
            )
            return summary.strip()

        except Exception as e:
            logger.error("Failed to generate conversation summary", conversation_id=str(conversation_id), error=str(e))
            return None

    async def prune_memories(
        self,
        contact_id: uuid.UUID,
        business_id: uuid.UUID,
        provider: BaseLLMProvider,
        model_name: str,
    ) -> None:
        """Consolidates and de-duplicates customer fact lists using LLM prompts to prune redundancies."""
        query = (
            select(ContactMemory)
            .where(ContactMemory.contact_id == contact_id)
            .where(ContactMemory.business_id == business_id)
            .where(ContactMemory.is_active.is_(True))
        )
        res = await self.db.execute(query)
        memories = list(res.scalars().all())

        if len(memories) < 4:
            # No need to prune if facts list is small
            return

        memory_lines = []
        for i, m in enumerate(memories):
            memory_lines.append(f"{i+1}. [Type: {m.memory_type}] {m.content}")

        memory_list_str = "\n".join(memory_lines)

        system_prompt = (
            "You are an AI memory manager. Analyze the following list of customer facts/preferences. "
            "Combine redundant items, reconcile contradicting items by keeping the newest truth, "
            "and output a cleaned consolidated list. "
            "You MUST output your response strictly as a JSON array of objects with 'type' and 'content' keys:\n"
            '[\n  {"type": "fact", "content": "Customer prefers WhatsApp messaging"}\n]\n'
            "Supported types are: summary, preference, fact, purchase, custom."
        )

        try:
            reply = await provider.generate_response(
                system_prompt=system_prompt,
                conversation_history=[],
                user_message=f"Facts List:\n{memory_list_str}",
                model_name=model_name,
                temperature=0.3,
            )

            # Extract json array block
            json_start = reply.find("[")
            json_end = reply.rfind("]") + 1
            if json_start != -1 and json_end != -1:
                cleaned_json = reply[json_start:json_end]
                new_memories_data = json.loads(cleaned_json)

                # Deactivate all old memories
                for m in memories:
                    m.is_active = False
                    self.db.add(m)

                # Insert new pruned memories
                for item in new_memories_data:
                    m_type = item.get("type", "fact")
                    m_content = item.get("content", "")
                    if m_content:
                        new_mem = ContactMemory(
                            contact_id=contact_id,
                            business_id=business_id,
                            memory_type=m_type,
                            content=m_content,
                            relevance_score=1.0,
                            last_accessed_at=datetime.now(timezone.utc),
                        )
                        self.db.add(new_mem)

                await self.db.commit()
                logger.info("Consolidated customer facts list successfully", contact_id=str(contact_id))

        except Exception as e:
            logger.error("Failed to prune/consolidate customer memories", contact_id=str(contact_id), error=str(e))
