import uuid
from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.tag import Tag
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Repository handling custom querying, filtering, and state updates for Conversations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Conversation, db)

    async def search_conversations(
        self,
        business_id: uuid.UUID,
        status: str | None = None,
        tags: list[str] | None = None,
        search_query: str | None = None,
        assigned_agent_id: uuid.UUID | None = None,
        unassigned: bool | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Sequence[Conversation]:
        """Queries and filters conversations based on status, tags, search terms, assignees, and pagination."""
        query = (
            select(Conversation)
            .where(Conversation.business_id == business_id)
            .options(joinedload(Conversation.contact), selectinload(Conversation.tags))
        )

        if status:
            query = query.where(Conversation.status == status)

        if tags:
            # Join tags association and filter by matching names
            query = query.join(Conversation.tags).where(Tag.name.in_(tags))

        if search_query:
            # Join contacts and search across phone number or customer display names
            query = query.join(Conversation.contact).where(
                or_(
                    Contact.name.ilike(f"%{search_query}%"),
                    Contact.phone_number.ilike(f"%{search_query}%"),
                )
            )

        if unassigned:
            query = query.where(Conversation.assigned_agent_id.is_(None))
        elif assigned_agent_id:
            query = query.where(Conversation.assigned_agent_id == assigned_agent_id)

        # Order by latest update (last messaging interaction)
        query = query.order_by(Conversation.updated_at.desc()).offset(skip).limit(limit)

        res = await self.db.execute(query)
        return res.scalars().unique().all()

    async def reset_unread_count(self, conversation_id: uuid.UUID) -> None:
        """Resets the unread message tracking counter for a conversation to 0."""
        conv = await self.get(conversation_id)
        if conv:
            conv.unread_count = 0
            self.db.add(conv)
            await self.db.commit()
