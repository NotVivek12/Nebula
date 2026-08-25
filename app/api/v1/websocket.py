"""
Authenticated WebSocket endpoint.

Authentication:
  - Client must provide a valid JWT access token as a query parameter: ?token=<jwt>
  - The token is validated and the user's membership in the requested business is verified
  - Unauthenticated or unauthorized connections are rejected before accept()

Multi-instance broadcasting:
  - In-memory manager works for single-instance deployments
  - For horizontal scaling, use Redis pub/sub via the pubsub module
"""

import uuid

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.logging import logger
from app.core.security import decode_access_token
from app.db.session import AsyncSessionLocal
from app.models.business_user import BusinessUser
from app.models.role import Role
from app.repositories.user import UserRepository
from app.services.websocket_manager import manager

router = APIRouter()


async def _authenticate_websocket(
    websocket: WebSocket,
    business_id: uuid.UUID,
    token: str | None,
) -> bool:
    """
    Validates JWT token and verifies tenant membership for a WebSocket connection.

    Returns True if authentication succeeds.
    Closes the WebSocket with an appropriate code on failure.
    """
    if not token:
        logger.warning("WebSocket connection rejected: no token provided", business_id=str(business_id))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    # Validate JWT
    user_id_str = decode_access_token(token)
    if not user_id_str:
        logger.warning("WebSocket connection rejected: invalid token", business_id=str(business_id))
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    # Verify tenant membership
    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    async with AsyncSessionLocal() as db:
        user_repo = UserRepository(db)
        user = await user_repo.get(str(user_uuid))

        if not user or not user.is_active:
            logger.warning(
                "WebSocket rejected: user not found or inactive",
                user_id=user_id_str,
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

        membership_query = (
            select(BusinessUser)
            .where(BusinessUser.user_id == user_uuid)
            .where(BusinessUser.business_id == business_id)
            .options(selectinload(BusinessUser.role).selectinload(Role.permissions))
        )
        res = await db.execute(membership_query)
        membership = res.scalar_one_or_none()

        if not membership:
            logger.warning(
                "WebSocket rejected: user not member of business",
                user_id=user_id_str,
                business_id=str(business_id),
            )
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False

    logger.info(
        "WebSocket authenticated",
        user_id=user_id_str,
        business_id=str(business_id),
    )
    return True


@router.websocket("/{business_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    business_id: uuid.UUID,
    token: str | None = Query(None, description="JWT access token for authentication"),
) -> None:
    """
    Authenticated multi-tenant WebSocket channel.

    Connect: ws://<host>/api/v1/ws/<business_id>?token=<jwt_access_token>
    """
    # Authenticate BEFORE accepting the connection
    authenticated = await _authenticate_websocket(websocket, business_id, token)
    if not authenticated:
        return  # Connection already closed in _authenticate_websocket

    await manager.connect(websocket, business_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, business_id)
        logger.info("WebSocket disconnected", business_id=str(business_id))
    except Exception as exc:
        logger.error(
            "WebSocket error",
            business_id=str(business_id),
            error=str(exc),
        )
        manager.disconnect(websocket, business_id)
