from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.ai.tools.base import Tool
from app.models.contact import Contact


class CreateLeadTool(Tool):
    """Tool to create a customer contact lead in the active business database."""

    @property
    def name(self) -> str:
        return "create_lead"

    @property
    def description(self) -> str:
        return "Creates a new customer contact lead profile in the tenant's database."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "phone_number": {"type": "string", "description": "Destination contact phone number"},
                "name": {"type": "string", "description": "Customer display name"},
                "lead_status": {"type": "string", "description": "Status key (e.g., new, qualified)"},
            },
            "required": ["phone_number", "name"],
        }

    @property
    def required_permissions(self) -> list[str]:
        return ["contacts:write"]

    async def execute(self, **kwargs: Any) -> Any:
        db = kwargs.pop("db", None)
        business_id = kwargs.pop("business_id", None)

        if not db or not business_id:
            raise ValueError("Database session and business context are required to run create_lead.")

        phone_number = kwargs.get("phone_number")
        name = kwargs.get("name")
        lead_status = kwargs.get("lead_status", "new")

        # Check if contact already exists
        query = (
            select(Contact)
            .where(Contact.phone_number == phone_number)
            .where(Contact.business_id == business_id)
        )
        res = await db.execute(query)
        existing = res.scalar_one_or_none()

        if existing:
            return {"status": "exists", "contact_id": str(existing.id), "name": existing.name}

        # Create contact lead
        contact = Contact(
            phone_number=phone_number,
            name=name,
            lead_status=lead_status,
            business_id=business_id,
            last_interaction=datetime.now(timezone.utc),
        )
        db.add(contact)
        await db.flush()

        return {
            "status": "created",
            "contact_id": str(contact.id),
            "phone_number": phone_number,
            "name": name,
        }
