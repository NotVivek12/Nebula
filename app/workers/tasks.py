"""
Celery worker tasks.

CRITICAL RULES for all tasks:
1. Never accept a FastAPI/SQLAlchemy session as a parameter.
2. Always create a fresh AsyncSession via AsyncSessionLocal.
3. Every task must be idempotent (safe to retry).
4. Always commit or rollback explicitly — never leave open transactions.
5. Use structured logging with task_id for traceability.
"""

import asyncio
import json
import uuid
from typing import Any

from celery import Task
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.db.session import AsyncSessionLocal
from app.models.conversation import Conversation
from app.models.message import Message
from app.workers.celery_app import celery_app


def run_async(coro: Any) -> Any:
    """Run an async coroutine from a synchronous Celery task."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ──────────────────────────────────────────────────────────────
# Outbound Message Delivery Task
# ──────────────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.send_outgoing_message_task",
    bind=True,
    max_retries=3,
    default_retry_delay=30,  # seconds; doubles with exponential backoff
    acks_late=True,
)
def send_outgoing_message_task(self: Task, message_id_str: str) -> dict[str, Any]:
    """
    Celery task: dispatches a queued outbound message to WhatsApp Cloud API.

    Retries up to 3 times with exponential backoff on transient failures.
    """
    return run_async(_send_outgoing_message(self, message_id_str))


async def _send_outgoing_message(task: Task, message_id_str: str) -> dict[str, Any]:
    """Async implementation of outbound message dispatch."""
    message_uuid = uuid.UUID(message_id_str)

    async with AsyncSessionLocal() as db:
        # Fetch message with related conversation and contact
        query = (
            select(Message)
            .where(Message.id == message_uuid)
            .options(
                selectinload(Message.conversation).selectinload(Conversation.contact)
            )
        )
        res = await db.execute(query)
        message = res.scalar_one_or_none()

        if not message:
            logger.error("Outbound message not found", message_id=message_id_str)
            return {"status": "not_found"}

        # Idempotency — avoid double delivery
        if message.status not in ("queued", "pending"):
            logger.info(
                "Outbound message already processed, skipping",
                message_id=message_id_str,
                current_status=message.status,
            )
            return {"status": "already_processed"}

        conversation = message.conversation
        recipient_phone = conversation.contact.phone_number
        business_id = conversation.business_id

        # Resolve messaging provider
        try:
            from app.services.messaging.dispatcher import (
                get_messaging_provider,  # noqa: PLC0415
            )
            provider = await get_messaging_provider(business_id, db)
        except Exception as exc:
            logger.error(
                "Could not resolve messaging provider",
                business_id=str(business_id),
                error=str(exc),
            )
            message.status = "failed"
            message.error_message = f"Provider resolution failed: {exc}"
            db.add(message)
            await db.commit()
            # Retry on provider resolution failure (may be transient)
            raise task.retry(exc=exc, countdown=2 ** task.request.retries * 30)  # noqa: B904

        # Parse content (supports JSON-encoded structured messages)
        content_str = message.content
        api_response: dict[str, Any] | None = None

        try:
            if content_str.strip().startswith("{") and content_str.strip().endswith("}"):
                payload = json.loads(content_str)
                msg_type = payload.get("type", "text")

                if msg_type == "template":
                    api_response = await provider.send_template(
                        to=recipient_phone,
                        template_name=payload.get("template_name", ""),
                        language_code=payload.get("language_code", "en_US"),
                        components=payload.get("components"),
                    )
                elif msg_type == "interactive":
                    api_response = await provider.send_interactive_buttons(
                        to=recipient_phone,
                        body_text=payload.get("body_text", ""),
                        buttons=payload.get("buttons", []),
                    )
                elif msg_type == "image":
                    api_response = await provider.send_image(
                        to=recipient_phone,
                        image_url=payload.get("image_url", ""),
                        caption=payload.get("caption"),
                    )
                elif msg_type == "document":
                    api_response = await provider.send_document(
                        to=recipient_phone,
                        document_url=payload.get("document_url", ""),
                        filename=payload.get("filename"),
                    )
                else:
                    api_response = await provider.send_text(to=recipient_phone, text=content_str)
            else:
                api_response = await provider.send_text(to=recipient_phone, text=content_str)

            # Extract provider message ID from response
            if api_response:
                meta_messages = api_response.get("messages", [])
                if meta_messages:
                    message.provider_message_id = meta_messages[0].get("id")
            message.status = "sent"

            logger.info(
                "Outbound message dispatched",
                message_id=message_id_str,
                provider_message_id=message.provider_message_id,
            )

        except Exception as exc:
            attempt = task.request.retries
            max_retries = task.max_retries or 3

            logger.error(
                "Outbound message send failed",
                message_id=message_id_str,
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(exc),
            )

            if attempt >= max_retries:
                # Dead-letter: mark permanently failed
                message.status = "failed"
                message.error_message = f"Max retries exceeded. Last error: {exc}"
                db.add(message)
                await db.commit()
                return {"status": "dead_lettered", "error": str(exc)}

            # Exponential backoff: 30s, 60s, 120s
            countdown = 30 * (2 ** attempt)
            raise task.retry(exc=exc, countdown=countdown)  # noqa: B904

        db.add(message)
        await db.commit()
        return {"status": "sent", "provider_message_id": message.provider_message_id}


# ──────────────────────────────────────────────────────────────
# Inbound Message AI Processing Task
# ──────────────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.process_incoming_message_task",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
    acks_late=True,
)
def process_incoming_message_task(
    self: Task,
    conversation_id_str: str,
    business_id_str: str,
) -> dict[str, Any]:
    """
    Celery task: runs AI inference on an inbound conversation and sends a response.

    Creates its own DB session — never touches FastAPI request sessions.
    """
    return run_async(
        _process_incoming_message(self, conversation_id_str, business_id_str)
    )


async def _process_incoming_message(
    task: Task,
    conversation_id_str: str,
    business_id_str: str,
) -> dict[str, Any]:
    """Async implementation of AI response pipeline."""
    conversation_id = uuid.UUID(conversation_id_str)
    business_id = uuid.UUID(business_id_str)

    async with AsyncSessionLocal() as db:
        try:
            from app.services.agent.orchestrator import AIOrchestrator  # noqa: PLC0415

            orchestrator = AIOrchestrator()
            result = await orchestrator.process_message(
                conversation_id=conversation_id,
                business_id=business_id,
                db=db,
            )

            logger.info(
                "AI processing completed",
                conversation_id=conversation_id_str,
                result_status=result.get("status"),
            )
            return result

        except Exception as exc:
            logger.error(
                "AI processing failed",
                conversation_id=conversation_id_str,
                error=str(exc),
            )
            attempt = task.request.retries
            max_retries = task.max_retries or 2
            if attempt < max_retries:
                raise task.retry(exc=exc, countdown=10 * (2 ** attempt))  # noqa: B904
            return {"status": "failed", "error": str(exc)}


# ──────────────────────────────────────────────────────────────
# Workflow Execution Task
# ──────────────────────────────────────────────────────────────

@celery_app.task(
    name="app.workers.tasks.run_workflow_task",
    bind=True,
    max_retries=1,
    acks_late=True,
)
def run_workflow_task(
    self: Task,
    run_id_str: str,
) -> dict[str, Any]:
    """
    Celery task: executes a workflow run by ID.

    The run must already exist in the database in 'running' or 'pending' state.
    """
    return run_async(_run_workflow(self, run_id_str))


async def _run_workflow(task: Task, run_id_str: str) -> dict[str, Any]:
    """Async implementation of workflow execution."""
    run_id = uuid.UUID(run_id_str)

    async with AsyncSessionLocal() as db:
        try:
            from app.services.workflow.engine import WorkflowEngine  # noqa: PLC0415

            engine = WorkflowEngine()
            await engine.execute_run(run_id, db)
            return {"status": "completed", "run_id": run_id_str}

        except Exception as exc:
            logger.error(
                "Workflow execution failed",
                run_id=run_id_str,
                error=str(exc),
            )
            return {"status": "failed", "error": str(exc)}
