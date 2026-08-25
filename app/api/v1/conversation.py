import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.authz import RequirePermission
from app.db.session import get_db
from app.models.business_user import BusinessUser
from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.contact import ContactRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.tag import TagRepository
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    StatusAssignRequest,
    TagsAssignRequest,
)
from app.schemas.human_support import (
    ConversationAssignRequest,
    InternalCommentCreate,
    TypingIndicatorRequest,
)
from app.services.websocket_manager import manager

router = APIRouter()


@router.get("", response_model=list[ConversationResponse])
async def search_conversations(
    status: str | None = Query(None, description="Filter by status (active, closed, archived, escalated)"),
    tags: list[str] | None = Query(None, description="Filter by tag names"),
    search: str | None = Query(None, description="Search contact name or phone number"),
    assigned_agent_id: uuid.UUID | None = Query(None, description="Filter by assigned agent ID"),
    unassigned: bool | None = Query(None, description="Filter unassigned conversations"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    membership: BusinessUser = Depends(RequirePermission("conversations:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Lists and searches conversation threads with paginated filters (requires conversations:read permission)."""
    repo = ConversationRepository(db)
    conversations = await repo.search_conversations(
        business_id=membership.business_id,
        status=status,
        tags=tags,
        search_query=search,
        assigned_agent_id=assigned_agent_id,
        unassigned=unassigned,
        skip=skip,
        limit=limit,
    )
    return conversations


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    payload: ConversationCreate,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Manually opens a new conversation thread for a customer contact (requires conversations:write permission)."""
    contact_repo = ContactRepository(db)
    contact = await contact_repo.get(payload.contact_id)

    if not contact or contact.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contact not found within this business tenant.",
        )

    # Check for existing active conversation for this contact
    repo = ConversationRepository(db)
    existing = await db.execute(
        select(Conversation)
        .where(Conversation.contact_id == contact.id)
        .where(Conversation.business_id == membership.business_id)
        .where(Conversation.status == "active")
        .options(selectinload(Conversation.tags))
    )
    active_conv = existing.scalar_one_or_none()
    if active_conv:
        return active_conv

    # Create new active conversation
    new_conv = Conversation(
        contact_id=contact.id,
        business_id=membership.business_id,
        status="active",
        unread_count=0,
        is_ai_controlled=True,
    )
    created = await repo.create(new_conv)
    # Refresh to eager load relationships cleanly for response
    query = select(Conversation).where(Conversation.id == created.id).options(selectinload(Conversation.tags))
    res = await db.execute(query)
    return res.scalar_one()


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: uuid.UUID,
    membership: BusinessUser = Depends(RequirePermission("conversations:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieves conversation thread parameters by ID (requires conversations:read permission)."""
    query = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.business_id == membership.business_id)
        .options(selectinload(Conversation.tags))
    )
    res = await db.execute(query)
    conversation = res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found within this business tenant.",
        )

    return conversation


@router.get("/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    membership: BusinessUser = Depends(RequirePermission("conversations:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Retrieves paginated conversation message history, resetting the unread count (requires conversations:read)."""
    repo = ConversationRepository(db)
    conversation = await repo.get(conversation_id)

    if not conversation or conversation.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found within this business tenant.",
        )

    # 1. Reset unread counts as the agent is opening/reading the history logs
    if conversation.unread_count > 0:
        await repo.reset_unread_count(conversation.id)

    # 2. Fetch paginated messages (internal comments are interleaved dynamically)
    query = (
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at.asc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(query)
    messages = res.scalars().all()

    return {
        "conversation_id": conversation.id,
        "unread_count": 0,
        "messages": messages,
    }


@router.post("/{conversation_id}/close", response_model=ConversationResponse)
async def close_conversation(
    conversation_id: uuid.UUID,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Closes an active conversation thread lifecycle (requires conversations:write permission)."""
    repo = ConversationRepository(db)
    conversation = await repo.get(conversation_id)

    if not conversation or conversation.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found within this business tenant.",
        )

    updated = await repo.update(conversation, {"status": "closed"})
    query = select(Conversation).where(Conversation.id == updated.id).options(selectinload(Conversation.tags))
    res = await db.execute(query)
    return res.scalar_one()


@router.post("/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation_id: uuid.UUID,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Archives a conversation thread lifecycle (requires conversations:write permission)."""
    repo = ConversationRepository(db)
    conversation = await repo.get(conversation_id)

    if not conversation or conversation.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found within this business tenant.",
        )

    updated = await repo.update(conversation, {"status": "archived"})
    query = select(Conversation).where(Conversation.id == updated.id).options(selectinload(Conversation.tags))
    res = await db.execute(query)
    return res.scalar_one()


@router.post("/{conversation_id}/status", response_model=ConversationResponse)
async def assign_status(
    conversation_id: uuid.UUID,
    payload: StatusAssignRequest,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Assigns a custom status value to a conversation lifecycle (requires conversations:write permission)."""
    repo = ConversationRepository(db)
    conversation = await repo.get(conversation_id)

    if not conversation or conversation.business_id != membership.business_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found within this business tenant.",
        )

    updated = await repo.update(conversation, {"status": payload.status})
    query = select(Conversation).where(Conversation.id == updated.id).options(selectinload(Conversation.tags))
    res = await db.execute(query)
    return res.scalar_one()


@router.post("/{conversation_id}/tags", response_model=ConversationResponse)
async def assign_tags(
    conversation_id: uuid.UUID,
    payload: TagsAssignRequest,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Assigns custom tag labels to a conversation thread, creating new tags if necessary (requires conversations:write)."""
    repo = ConversationRepository(db)  # noqa: F841
    query = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.business_id == membership.business_id)
        .options(selectinload(Conversation.tags))
    )
    res = await db.execute(query)
    conversation = res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found within this business tenant.",
        )

    tag_repo = TagRepository(db)
    new_tags = []
    for tag_name in payload.tags:
        cleaned_name = tag_name.strip().lower()
        if cleaned_name:
            tag = await tag_repo.get_or_create_by_name(membership.business_id, cleaned_name)
            new_tags.append(tag)

    conversation.tags = new_tags
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return conversation


@router.post("/{conversation_id}/assign", response_model=ConversationResponse)
async def assign_conversation(
    conversation_id: uuid.UUID,
    payload: ConversationAssignRequest,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Assigns a conversation to an agent (takeover if self/different agent) (requires conversations:write)."""
    query = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.business_id == membership.business_id)
        .options(selectinload(Conversation.tags))
    )
    res = await db.execute(query)
    conversation = res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    assigned_id = payload.assigned_agent_id or membership.user_id
    conversation.assigned_agent_id = assigned_id
    conversation.is_ai_controlled = False
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Broadcast real-time update
    await manager.broadcast_to_tenant(
        membership.business_id,
        {
            "event": "conversation_assigned",
            "conversation_id": str(conversation.id),
            "assigned_agent_id": str(assigned_id),
        },
    )

    return conversation


@router.post("/{conversation_id}/release", response_model=ConversationResponse)
async def release_conversation(
    conversation_id: uuid.UUID,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Releases conversation assignment back to shared inbox, resuming AI control (requires conversations:write)."""
    query = (
        select(Conversation)
        .where(Conversation.id == conversation_id)
        .where(Conversation.business_id == membership.business_id)
        .options(selectinload(Conversation.tags))
    )
    res = await db.execute(query)
    conversation = res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    conversation.assigned_agent_id = None
    conversation.is_ai_controlled = True
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    # Broadcast real-time update
    await manager.broadcast_to_tenant(
        membership.business_id,
        {
            "event": "conversation_released",
            "conversation_id": str(conversation.id),
        },
    )

    return conversation


@router.post("/{conversation_id}/comment")
async def add_internal_comment(
    conversation_id: uuid.UUID,
    payload: InternalCommentCreate,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Appends an internal comment note to a conversation (requires conversations:write)."""
    # Verify ownership
    query = select(Conversation).where(Conversation.id == conversation_id).where(Conversation.business_id == membership.business_id)
    res = await db.execute(query)
    conversation = res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    message = Message(
        sender_type="user",
        content=payload.content,
        status="sent",
        is_internal=True,
        conversation_id=conversation.id,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    # Broadcast real-time comment event to WebSockets
    await manager.broadcast_to_tenant(
        membership.business_id,
        {
            "event": "internal_comment_added",
            "conversation_id": str(conversation.id),
            "message": {
                "id": str(message.id),
                "sender_type": message.sender_type,
                "content": message.content,
                "is_internal": True,
                "created_at": message.created_at.isoformat(),
            },
        },
    )

    return {"status": "success", "message_id": str(message.id)}


@router.post("/{conversation_id}/typing")
async def publish_typing_indicator(
    conversation_id: uuid.UUID,
    payload: TypingIndicatorRequest,
    membership: BusinessUser = Depends(RequirePermission("conversations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Publishes a typing indicator status update to WebSockets (requires conversations:write)."""
    # Verify ownership
    query = select(Conversation).where(Conversation.id == conversation_id).where(Conversation.business_id == membership.business_id)
    res = await db.execute(query)
    conversation = res.scalar_one_or_none()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found.",
        )

    # Broadcast indicator status
    await manager.broadcast_to_tenant(
        membership.business_id,
        {
            "event": "typing_indicator",
            "conversation_id": str(conversation.id),
            "user_id": str(membership.user_id),
            "is_typing": payload.is_typing,
        },
    )

    return {"status": "published"}
