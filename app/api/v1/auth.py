"""
Authentication and onboarding routes.

POST /auth/onboard       — Register new business tenant + owner account
POST /auth/token         — Login with email + password
POST /auth/refresh       — Rotate refresh token
POST /auth/logout        — Revoke current session
POST /auth/logout-all    — Revoke all sessions for current user
POST /auth/invite        — Invite team member
POST /auth/accept-invite — Accept invitation and create account
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import RequirePermission
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.core.logging import logger
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    get_password_hash,
    hash_refresh_token,
    validate_password_strength,
    verify_password,
)
from app.db.session import get_db
from app.models.business import Business
from app.models.business_user import BusinessUser
from app.models.invitation import UserInvitation
from app.models.refresh_token import RefreshToken
from app.models.role import Permission, Role
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import Token, TokenRefreshRequest
from app.schemas.invitation import (
    InvitationAccept,
    InvitationCreate,
    InvitationResponse,
)
from app.schemas.user import (
    BusinessOnboard,
    BusinessOnboardResponse,
)

router = APIRouter()

# ──────────────────────────────────────────────────────────────
# Complete permission set for new tenants.
# This must include ALL permissions required by any protected route.
# ──────────────────────────────────────────────────────────────
_ALL_PERMISSIONS = [
    # Contacts
    "contacts:read",
    "contacts:write",
    # Conversations
    "conversations:read",
    "conversations:write",
    # Invitations
    "invitations:create",
    "invitations:accept",
    # Workflows
    "workflows:read",
    "workflows:write",
    # Tools (NOTE: tool routes check tools:*, not integrations:*)
    "tools:read",
    "tools:write",
    # Knowledge base
    "knowledge:read",
    "knowledge:write",
    # AI Agents
    "agents:read",
    "agents:write",
    # Integrations
    "integrations:read",
    "integrations:write",
    # Messaging (sending outbound messages)
    "messaging:send",
]


async def _get_or_create_permission(db: AsyncSession, name: str) -> Permission:
    """Returns existing Permission or creates a new one."""
    query = select(Permission).where(Permission.name == name)
    res = await db.execute(query)
    perm = res.scalar_one_or_none()
    if not perm:
        perm = Permission(
            name=name,
            description=f"Allows {name.replace(':', ' ')}",
        )
        db.add(perm)
        await db.flush()
    return perm


@router.post("/onboard", response_model=BusinessOnboardResponse, status_code=status.HTTP_201_CREATED)
async def onboard_tenant(
    payload: BusinessOnboard,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Onboards a new SaaS tenant: creates Business, seeds all roles/permissions, and Owner account.

    Owner role receives ALL permissions.
    Admin role receives read/write permissions (no invitation management by default).
    Member role receives read-only permissions.
    """
    # Password strength validation
    is_valid, pw_error = validate_password_strength(payload.owner_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_error)

    user_repo = UserRepository(db)
    existing_user = await user_repo.get_by_email(payload.owner_email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists.",
        )

    # 1. Create Business
    new_business = Business(name=payload.business_name)
    db.add(new_business)
    await db.flush()

    # 2. Create global User
    new_user = User(
        email=payload.owner_email,
        hashed_password=get_password_hash(payload.owner_password),
        full_name=payload.owner_full_name,
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # 3. Seed ALL permissions (ensures every route is accessible for Owner)
    all_perms: list[Permission] = []
    for perm_name in _ALL_PERMISSIONS:
        perm = await _get_or_create_permission(db, perm_name)
        all_perms.append(perm)

    # 4. Create Owner role (all permissions)
    owner_role = Role(
        name="Owner",
        is_system=True,
        business_id=new_business.id,
        permissions=all_perms,
    )
    db.add(owner_role)

    # 5. Admin role (read + write on core resources, no owner-only ops)
    admin_perms = [
        p for p in all_perms
        if any(p.name.startswith(prefix) for prefix in [
            "contacts:", "conversations:", "workflows:", "tools:",
            "knowledge:", "agents:", "integrations:", "messaging:",
        ])
    ]
    admin_role = Role(
        name="Admin",
        is_system=True,
        business_id=new_business.id,
        permissions=admin_perms,
    )
    db.add(admin_role)

    # 6. Member role (read-only on safe resources)
    member_perms = [p for p in all_perms if p.name.endswith(":read")]
    member_role = Role(
        name="Member",
        is_system=True,
        business_id=new_business.id,
        permissions=member_perms,
    )
    db.add(member_role)
    await db.flush()

    # 7. Bind owner user to business
    membership = BusinessUser(
        business_id=new_business.id,
        user_id=new_user.id,
        role_id=owner_role.id,
    )
    db.add(membership)
    await db.commit()

    logger.info(
        "Business tenant onboarded",
        business_id=str(new_business.id),
        owner_id=str(new_user.id),
        permissions_seeded=len(all_perms),
    )

    return {
        "business_id": new_business.id,
        "business_name": new_business.name,
        "owner": new_user,
    }


@router.post("/token", response_model=Token)
async def login_for_tokens(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Authenticates credentials and issues JWT access token + opaque refresh token.

    Refresh token is hashed before storage — raw token is returned to client only.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning("Authentication failed", email=form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )

    # Generate access token (with jti, iss, aud, type claims)
    access_token = create_access_token(subject=user.id)

    # Generate refresh token — only hash is stored
    raw_refresh, hashed_refresh = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    db_refresh = RefreshToken(
        token=hashed_refresh,  # Store hash, not raw token
        expires_at=expires_at,
        user_id=user.id,
    )
    db.add(db_refresh)
    await db.commit()

    logger.info("Session started", user_id=str(user.id))
    return Token(
        access_token=access_token,
        refresh_token=raw_refresh,  # Return raw token to client
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/refresh", response_model=Token)
async def refresh_session(
    payload: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Rotates refresh tokens — issues new access token and refresh token.

    The incoming raw refresh token is hashed and looked up in the database.
    """
    # Hash the incoming raw token to match DB storage
    hashed_incoming = hash_refresh_token(payload.refresh_token)

    query = (
        select(RefreshToken)
        .where(RefreshToken.token == hashed_incoming)
        .where(RefreshToken.is_revoked == False)  # noqa: E712
    )
    res = await db.execute(query)
    db_token = res.scalar_one_or_none()

    if not db_token or db_token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        logger.warning("Token refresh rejected: invalid or expired token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Revoke old token
    db_token.is_revoked = True
    db.add(db_token)

    # Issue new tokens
    new_access = create_access_token(subject=db_token.user_id)
    raw_new_refresh, hashed_new_refresh = generate_refresh_token()
    new_expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    new_db_refresh = RefreshToken(
        token=hashed_new_refresh,
        expires_at=new_expiry,
        user_id=db_token.user_id,
    )
    db.add(new_db_refresh)
    await db.commit()

    logger.info("Session rotated", user_id=str(db_token.user_id))
    return Token(
        access_token=new_access,
        refresh_token=raw_new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    payload: TokenRefreshRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Revokes the provided refresh token, ending the current session.

    The access token will expire naturally (no server-side revocation for stateless JWTs).
    """
    hashed = hash_refresh_token(payload.refresh_token)

    query = (
        select(RefreshToken)
        .where(RefreshToken.token == hashed)
        .where(RefreshToken.user_id == current_user.id)
        .where(RefreshToken.is_revoked == False)  # noqa: E712
    )
    res = await db.execute(query)
    db_token = res.scalar_one_or_none()

    if db_token:
        db_token.is_revoked = True
        db.add(db_token)
        await db.commit()

    logger.info("Session logged out", user_id=str(current_user.id))
    return {"status": "success", "detail": "Session revoked."}


@router.post("/logout-all", status_code=status.HTTP_200_OK)
async def logout_all(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Revokes ALL active refresh tokens for the current user.

    Use this after a suspected account compromise.
    """
    from sqlalchemy import update  # noqa: PLC0415

    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id)
        .where(RefreshToken.is_revoked == False)  # noqa: E712
        .values(is_revoked=True)
    )
    result = await db.execute(stmt)
    await db.commit()

    logger.info("All sessions revoked", user_id=str(current_user.id), revoked_count=result.rowcount)
    return {"status": "success", "detail": f"Revoked {result.rowcount} active session(s)."}


@router.post("/invite", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    payload: InvitationCreate,
    membership: BusinessUser = Depends(RequirePermission("invitations:create")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Invites a user to join the active business tenant."""
    import secrets  # noqa: PLC0415

    # Verify the target role belongs to this tenant
    query = (
        select(Role)
        .where(Role.id == payload.role_id)
        .where(Role.business_id == membership.business_id)
    )
    res = await db.execute(query)
    target_role = res.scalar_one_or_none()
    if not target_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role not found within this business tenant.",
        )

    # Check for active pending invite
    query = (
        select(UserInvitation)
        .where(UserInvitation.email == payload.email)
        .where(UserInvitation.business_id == membership.business_id)
        .where(UserInvitation.status == "pending")
    )
    res = await db.execute(query)
    existing_invite = res.scalar_one_or_none()
    if existing_invite:
        if existing_invite.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A pending invitation already exists for this email.",
            )
        else:
            existing_invite.status = "expired"
            db.add(existing_invite)

    invite_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=2)

    new_invite = UserInvitation(
        email=payload.email,
        token=invite_token,
        status="pending",
        expires_at=expires_at,
        business_id=membership.business_id,
        role_id=payload.role_id,
        invited_by_id=membership.user_id,
    )
    db.add(new_invite)
    await db.commit()

    logger.info("Team invitation sent", email=payload.email, business_id=str(membership.business_id))
    return new_invite


@router.post("/accept-invite", status_code=status.HTTP_200_OK)
async def accept_member_invite(
    payload: InvitationAccept,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Accepts a business invitation, creating account if needed."""
    # Password strength validation for new accounts
    if payload.password:
        is_valid, pw_error = validate_password_strength(payload.password)
        if not is_valid:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_error)

    query = (
        select(UserInvitation)
        .where(UserInvitation.token == payload.token)
        .where(UserInvitation.status == "pending")
    )
    res = await db.execute(query)
    invite = res.scalar_one_or_none()

    if not invite or invite.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        if invite:
            invite.status = "expired"
            db.add(invite)
            await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation is invalid, accepted, or has expired.",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_email(invite.email)
    if not user:
        user = User(
            email=invite.email,
            hashed_password=get_password_hash(payload.password or ""),
            full_name=payload.full_name,
            is_active=True,
        )
        db.add(user)
        await db.flush()

    # Check if already member
    query = (
        select(BusinessUser)
        .where(BusinessUser.business_id == invite.business_id)
        .where(BusinessUser.user_id == user.id)
    )
    res = await db.execute(query)
    existing_membership = res.scalar_one_or_none()
    if existing_membership:
        invite.status = "accepted"
        db.add(invite)
        await db.commit()
        return {"status": "success", "detail": "User is already a member of this business."}

    membership = BusinessUser(
        business_id=invite.business_id,
        user_id=user.id,
        role_id=invite.role_id,
    )
    db.add(membership)
    invite.status = "accepted"
    db.add(invite)
    await db.commit()

    logger.info("Invitation accepted", email=invite.email, business_id=str(invite.business_id))
    return {"status": "success", "detail": "Invitation accepted, membership established."}
