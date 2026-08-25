"""
Messaging API routes.

Webhook (Meta / WhatsApp Cloud API):
  GET  /webhooks/whatsapp  → Verification handshake
  POST /webhooks/whatsapp  → Inbound event processing

Outbound:
  POST /send               → Queue an outbound message
"""

from typing import Any

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    status,
)
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import RequirePermission
from app.core.config import settings
from app.core.logging import logger
from app.db.session import get_db
from app.models.business_user import BusinessUser
from app.schemas.messaging import MessageSendRequest
from app.services.messaging.signature import verify_whatsapp_signature

router = APIRouter()


@router.get("/webhooks/whatsapp", response_class=PlainTextResponse)
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
) -> str:
    """Responds to Meta webhook verification handshake."""
    if hub_mode == "subscribe" and hub_challenge:
        if hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            logger.info("Webhook verification handshake succeeded")
            return hub_challenge
        else:
            logger.warning("Webhook verification token mismatch")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Verification token mismatch",
            )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid handshake parameters",
    )


@router.post("/webhooks/whatsapp", status_code=status.HTTP_200_OK)
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256"),
) -> Any:
    """
    Central webhook ingestion point for WhatsApp Cloud API events.

    Processing steps:
    1. Read raw body bytes (required for HMAC verification).
    2. Verify X-Hub-Signature-256 header.
    3. Parse JSON payload.
    4. Persist raw event (idempotency fence).
    5. Enqueue processing job — return 200 immediately.

    Never performs AI inference inline. Returns 200 quickly so Meta does not retry.
    """
    # 1. Read raw body for signature check
    raw_body = await request.body()

    # 2. Verify signature — reject immediately if invalid
    if not verify_whatsapp_signature(raw_body, x_hub_signature_256):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid webhook signature",
        )

    # 3. Parse payload
    try:
        import json
        payload: dict[str, Any] = json.loads(raw_body)
    except Exception:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload is not valid JSON",
        )

    logger.info("Received WhatsApp Cloud API webhook event")

    # 4. Enqueue processing — do NOT block on AI inference
    #    The webhook_service handles idempotency and persistence.
    #    We import here to avoid circular imports at module level.
    from app.services.messaging.webhook_service import WebhookService

    service = WebhookService(db)

    # Run lightweight persistence (idempotency check + event log) synchronously
    # so we can return 200 with confidence the event is durable.
    # Heavy AI processing is enqueued to Celery.
    await service.process_event(payload)

    return {"status": "ok"}


@router.post("/send", status_code=status.HTTP_202_ACCEPTED)
async def send_message(
    payload: MessageSendRequest,
    background_tasks: BackgroundTasks,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Queues an outgoing WhatsApp message for background dispatch.

    Requires conversations:write permission.
    """
    from datetime import datetime, timezone

    from app.models.contact import Contact
    from app.models.conversation import Conversation
    from app.models.message import Message

    business_id = membership.business_id

    # Resolve or create contact
    contact_query = (
        select(Contact)
        .where(Contact.phone_number == payload.recipient)
        .where(Contact.business_id == business_id)
    )
    res = await db.execute(contact_query)
    contact = res.scalar_one_or_none()

    if not contact:
        contact = Contact(
            phone_number=payload.recipient,
            name="Outgoing Recipient",
            business_id=business_id,
            lead_status="new",
            last_interaction=datetime.now(timezone.utc),
        )
        db.add(contact)
        await db.flush()

    # Resolve or create active conversation
    conv_query = (
        select(Conversation)
        .where(Conversation.contact_id == contact.id)
        .where(Conversation.business_id == business_id)
        .where(Conversation.status == "active")
    )
    res = await db.execute(conv_query)
    conversation = res.scalar_one_or_none()

    if not conversation:
        conversation = Conversation(
            contact_id=contact.id,
            business_id=business_id,
            status="active",
        )
        db.add(conversation)
        await db.flush()

    # Persist queued outbound message
    new_message = Message(
        sender_type="user",
        content=payload.content,
        status="queued",
        conversation_id=conversation.id,
    )
    db.add(new_message)
    await db.commit()

    # Enqueue Celery task for durable delivery
    from app.workers.celery_app import celery_app  # noqa: PLC0415
    celery_app.send_task(
        "app.workers.tasks.send_outgoing_message_task",
        args=[str(new_message.id)],
    )

    logger.info(
        "Outbound message queued",
        message_id=str(new_message.id),
        recipient=payload.recipient,
    )

    return {
        "status": "queued",
        "message_id": str(new_message.id),
        "recipient": payload.recipient,
    }
