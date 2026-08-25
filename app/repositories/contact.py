import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contact import Contact
from app.repositories.base import BaseRepository


class ContactRepository(BaseRepository[Contact]):
    """Repository handling customer Contact database operations."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(Contact, db)

    async def get_by_phone(self, business_id: uuid.UUID, phone_number: str) -> Contact | None:
        """Retrieves a customer contact record by phone number in a tenant business context."""
        query = (
            select(Contact)
            .where(Contact.business_id == business_id)
            .where(Contact.phone_number == phone_number)
        )
        res = await self.db.execute(query)
        return res.scalar_one_or_none()
