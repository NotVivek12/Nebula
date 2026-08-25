"""
Celery application configuration.

Uses Redis as both broker and result backend.
All tasks must create their own database sessions — never pass FastAPI request sessions.
"""

from celery import Celery

from app.core.config import settings


def create_celery_app() -> Celery:
    """Creates and configures the Celery application."""
    app = Celery(
        "nebula",
        broker=settings.effective_celery_broker,
        backend=settings.effective_celery_backend,
        include=[
            "app.workers.tasks",
        ],
    )

    app.conf.update(
        # Serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        # Timezone
        timezone="UTC",
        enable_utc=True,
        # Task routing
        task_default_queue="default",
        task_queues={
            "default": {},
            "ai_processing": {},
            "outbound_messages": {},
            "workflow_execution": {},
        },
        task_routes={
            "app.workers.tasks.process_incoming_message_task": {"queue": "ai_processing"},
            "app.workers.tasks.send_outgoing_message_task": {"queue": "outbound_messages"},
            "app.workers.tasks.run_workflow_task": {"queue": "workflow_execution"},
        },
        # Retry policy defaults
        task_acks_late=True,               # Acknowledge task only after it completes
        task_reject_on_worker_lost=True,   # Re-queue if worker dies
        worker_prefetch_multiplier=1,      # One task per worker at a time for fairness
        # Result expiry
        result_expires=3600,  # 1 hour
        # Logging
        worker_hijack_root_logger=False,
    )

    return app


celery_app = create_celery_app()
