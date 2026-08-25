import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.repositories.base import BaseRepository


class TagRepository(BaseRepository[Tag]):
    """Repository handling custom tag lookups and creations per tenant business."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Tag, db)

    async def get_by_name(self, business_id: uuid.UUID, name: str) -> Tag | None:
        """Retrieves a tag by name within a business tenant's context."""
        query = select(Tag).where(Tag.business_id == business_id).where(Tag.name == name)
        res = await self.db.execute(query)
        return res.scalar_one_or_none()

    async def get_or_create_by_name(self, business_id: uuid.UUID, name: str) -> Tag:
        """Finds a tag by name, or creates a new one if not found."""
        tag = await self.get_by_name(business_id, name)
        if not tag:
            tag = Tag(name=name, business_id=business_id)
            self.db.add(tag)
            await self.db.flush()
        return tag
