from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.orchestrator import AIOrchestrator
from app.core.authz import RequirePermission
from app.db.session import get_db
from app.models.business_user import BusinessUser
from app.schemas.chat import ChatMessageRequest

router = APIRouter()


@router.post("", status_code=status.HTTP_200_OK)
async def chat_message(
    payload: ChatMessageRequest,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Interacts with the AI Orchestrator thread directly (requires conversations:write permission)."""
    orchestrator = AIOrchestrator()
    try:
        reply = await orchestrator.process_message(
            business_id=membership.business_id,
            conversation_id=payload.conversation_id,
            user_message=payload.message,
            db=db,
        )
        return {
            "reply": reply,
            "conversation_id": str(payload.conversation_id),
            "business_id": str(membership.business_id),
        }
    except ValueError as e:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI orchestration failed: {e}",
        )
