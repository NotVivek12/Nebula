from fastapi import APIRouter

from app.api.v1 import (
    agent,
    auth,
    chat,
    contact,
    conversation,
    health,
    knowledge,
    messaging,
    metrics,
    tool,
    websocket,
    workflow,
)

api_router = APIRouter()

# Register sub-routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(messaging.router, tags=["messaging"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(workflow.router, prefix="/workflow", tags=["workflow"])
api_router.include_router(tool.router, prefix="/tool", tags=["tools"])
api_router.include_router(conversation.router, prefix="/conversation", tags=["conversations"])
api_router.include_router(contact.router, prefix="/contact", tags=["contacts"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websockets"])
api_router.include_router(agent.router, prefix="/agent", tags=["agents"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
