"""
WhatsApp webhook event service.

Responsibilities:
- Idempotency: reject duplicate provider_message_ids
- Persist raw webhook events
- Create/update contacts, conversations, messages
- Enqueue AI processing task (never inline)
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.contact import Contact
from app.models.conversation import Conversation
from app.models.integration import Integration
from app.models.message import Message
from app.models.webhook_event import WebhookEvent
from app.services.messaging.media import MediaDownloadService


class WebhookService:
    """Processes incoming WhatsApp webhook events with idempotency protection."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def process_event(self, raw_payload: dict[str, Any]) -> None:
        """
        Central ingestion pipeline:
        1. Extract provider metadata
        2. Resolve tenant from WhatsApp phone_number_id
        3. Idempotency fence using provider_message_id
        4. Persist event log
        5. Create/update domain objects
        6. Enqueue AI processing via Celery
        """
        # 1. Extract metadata
        try:
            entry = raw_payload.get("entry", [])[0]
            change = entry.get("changes", [])[0]
            value = change.get("value", {})
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")
        except (IndexError, KeyError, AttributeError):
            logger.warning("Webhook payload format unparseable, missing metadata")
            return

        if not phone_number_id:
            logger.warning("Webhook metadata missing phone_number_id")
            return

        # 2. Resolve tenant
        query = select(Integration).where(Integration.provider == "whatsapp")
        res = await self.db.execute(query)
        integrations = res.scalars().all()

        business_id = None
        access_token: str | None = None
        for integration in integrations:
            creds = integration.credentials
            if str(creds.get("phone_number_id")) == str(phone_number_id):
                business_id = integration.business_id
                access_token = creds.get("access_token")
                break

        if not business_id:
            logger.warning(
                "No business integration found for phone_number_id",
                phone_id=phone_number_id,
            )
            # Still persist the raw event for debugging
            event = WebhookEvent(
                provider="whatsapp",
                event_type="unknown",
                payload=raw_payload,
                processed=False,
            )
            self.db.add(event)
            await self.db.commit()
            return

        # 3. Determine event type
        event_type = "unknown"
        if "messages" in value:
            event_type = "messages"
        elif "statuses" in value:
            event_type = "statuses"

        # 4. Persist raw event (before any processing — this is the idempotency anchor)
        event = WebhookEvent(
            provider="whatsapp",
            event_type=event_type,
            payload=raw_payload,
            processed=False,
            business_id=business_id,
        )
        self.db.add(event)
        await self.db.flush()

        # 5. Delegate to handlers
        conversation_ids: list[Any] = []
        if "messages" in value:
            conversation_ids = await self._handle_messages(
                value.get("messages", []),
                value.get("contacts", []),
                business_id,
                access_token,
            )
        elif "statuses" in value:
            await self._handle_statuses(value.get("statuses", []), business_id)

        # Mark event processed
        event.processed = True
        self.db.add(event)
        await self.db.commit()

        # 6. Enqueue AI processing for each new inbound message conversation
        for conv_id in conversation_ids:
            try:
                from app.workers.celery_app import celery_app  # noqa: PLC0415
                celery_app.send_task(
                    "app.workers.tasks.process_incoming_message_task",
                    args=[str(conv_id), str(business_id)],
                )
                logger.info("AI processing enqueued", conversation_id=str(conv_id))
            except Exception as exc:
                logger.error(
                    "Failed to enqueue AI processing task",
                    conversation_id=str(conv_id),
                    error=str(exc),
                )

    async def _handle_messages(
        self,
        messages_payload: list[dict[str, Any]],
        contacts_payload: list[dict[str, Any]],
        business_id: Any,
        access_token: str | None,
    ) -> list[Any]:
        """
        Processes incoming customer messages.

        Returns list of conversation IDs that received new messages.
        Idempotency: skips messages whose provider_message_id already exists.
        """
        affected_conversation_ids: list[Any] = []

        for msg in messages_payload:
            sender_phone = msg.get("from")
            message_id = msg.get("id")
            msg_type = msg.get("type", "text")

            if not sender_phone or not message_id:
                continue

            # IDEMPOTENCY CHECK — skip if we already processed this provider message
            dup_query = select(Message).where(Message.provider_message_id == message_id)
            dup_res = await self.db.execute(dup_query)
            if dup_res.scalar_one_or_none():
                logger.info(
                    "Duplicate webhook message skipped (idempotency)",
                    provider_message_id=message_id,
                )
                continue

            # Resolve contact name from contacts block
            sender_name = "WhatsApp User"
            for c in contacts_payload:
                if c.get("wa_id") == sender_phone:
                    sender_name = c.get("profile", {}).get("name", sender_name)
                    break

            # Find or create Contact
            contact_query = (
                select(Contact)
                .where(Contact.phone_number == sender_phone)
                .where(Contact.business_id == business_id)
            )
            res = await self.db.execute(contact_query)
            contact = res.scalar_one_or_none()

            if not contact:
                contact = Contact(
                    phone_number=sender_phone,
                    name=sender_name,
                    business_id=business_id,
                    lead_status="new",
                    last_interaction=datetime.now(timezone.utc),
                )
                self.db.add(contact)
                await self.db.flush()
            else:
                contact.name = sender_name
                contact.last_interaction = datetime.now(timezone.utc)
                self.db.add(contact)

            # Find or create active Conversation
            conv_query = (
                select(Conversation)
                .where(Conversation.contact_id == contact.id)
                .where(Conversation.business_id == business_id)
                .where(Conversation.status == "active")
            )
            res = await self.db.execute(conv_query)
            conversation = res.scalar_one_or_none()

            if not conversation:
                conversation = Conversation(
                    contact_id=contact.id,
                    business_id=business_id,
                    status="active",
                    unread_count=1,
                )
                self.db.add(conversation)
                await self.db.flush()
            else:
                conversation.unread_count = (conversation.unread_count or 0) + 1
                self.db.add(conversation)

            # Resolve message content
            content = "Unsupported message type"
            if msg_type == "text":
                content = msg.get("text", {}).get("body", "")
            elif msg_type == "interactive":
                interactive = msg.get("interactive", {})
                btn_reply = interactive.get("button_reply", {})
                content = btn_reply.get("title", btn_reply.get("id", ""))
            elif msg_type in ("image", "document", "audio", "video", "voice"):
                media_meta = msg.get(msg_type, {})
                media_id = media_meta.get("id")
                content = f"[Media: {msg_type}, ID: {media_id}]"

                if media_id and access_token:
                    try:
                        downloader = MediaDownloadService(access_token)
                        local_path = await downloader.download_media(media_id)
                        if local_path:
                            content = local_path
                    except Exception as exc:
                        logger.warning(
                            "Media download failed",
                            media_id=media_id,
                            error=str(exc),
                        )

            # Persist message
            new_msg = Message(
                sender_type="contact",
                content=content,
                status="delivered",
                provider_message_id=message_id,
                conversation_id=conversation.id,
            )
            self.db.add(new_msg)
            await self.db.flush()

            logger.info(
                "Inbound message persisted",
                provider_message_id=message_id,
                conversation_id=str(conversation.id),
            )

            if conversation.id not in affected_conversation_ids:
                affected_conversation_ids.append(conversation.id)

        return affected_conversation_ids

    async def _handle_statuses(
        self, statuses_payload: list[dict[str, Any]], business_id: Any
    ) -> None:
        """Processes delivery/read status receipts, updating message state."""
        for status_item in statuses_payload:
            msg_id = status_item.get("id")
            recipient_status = status_item.get("status")  # sent, delivered, read, failed

            if not msg_id or not recipient_status:
                continue

            query = select(Message).where(Message.provider_message_id == msg_id)
            res = await self.db.execute(query)
            message = res.scalar_one_or_none()

            if message:
                message.status = recipient_status
                if recipient_status == "failed":
                    errors = status_item.get("errors", [])
                    err_msg = (
                        errors[0].get("title", "Unknown failure reason")
                        if errors
                        else "Delivery failed"
                    )
                    message.error_message = err_msg
                    logger.warning(
                        "Message delivery failed",
                        message_id=str(message.id),
                        error=err_msg,
                    )
                self.db.add(message)
                logger.info(
                    "Message status updated",
                    message_id=str(message.id),
                    status=recipient_status,
                )
