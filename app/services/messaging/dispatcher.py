import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import Integration
from app.services.messaging.base import BaseMessagingProvider
from app.services.messaging.whatsapp import WhatsAppMessagingProvider


async def get_messaging_provider(
    business_id: uuid.UUID,
    db: AsyncSession,
) -> BaseMessagingProvider:
    """Dynamically resolves and instantiates the active messaging provider for a tenant.

    Queries the active WhatsApp integration for the given business tenant,
    extracts credentials, and returns the instantiated provider client.
    """
    query = (
        select(Integration)
        .where(Integration.business_id == business_id)
        .where(Integration.provider == "whatsapp")
        .where(Integration.is_active.is_(True))
    )
    result = await db.execute(query)
    integration = result.scalar_one_or_none()

    if not integration:
        raise ValueError(f"No active WhatsApp integration found for business ID {business_id}")

    creds = integration.credentials
    phone_number_id = creds.get("phone_number_id")
    access_token = creds.get("access_token")

    if not phone_number_id or not access_token:
        raise ValueError(
            f"Invalid credentials mapping for WhatsApp integration on business {business_id}"
        )

    return WhatsAppMessagingProvider(
        phone_number_id=str(phone_number_id),
        access_token=str(access_token),
    )
