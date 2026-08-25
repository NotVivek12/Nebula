from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.registry import ToolRegistry
from app.core.authz import RequirePermission
from app.db.session import get_db
from app.models.business_user import BusinessUser
from app.models.role import Permission, Role
from app.schemas.tool import ToolExecuteRequest

router = APIRouter()
registry = ToolRegistry()


@router.get("")
async def list_tools(
    membership: BusinessUser = Depends(RequirePermission("integrations:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Lists all registered tools for AI discovery (requires integrations:read permission)."""
    # Load active user permissions list
    query = select(Permission.name).join(Role.permissions).where(Role.id == membership.role_id)
    res = await db.execute(query)
    permissions = list(res.scalars().all())

    # Return only tools the user has permissions to run
    tools = registry.list_tools(user_permissions=permissions)
    return tools


@router.post("/run")
async def run_tool(
    payload: ToolExecuteRequest,
    membership: BusinessUser = Depends(RequirePermission("integrations:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Executes a tool plugin using standard validation and audits (requires integrations:write permission)."""
    # Load user permissions for RBAC enforcement
    query = select(Permission.name).join(Role.permissions).where(Role.id == membership.role_id)
    res = await db.execute(query)
    permissions = list(res.scalars().all())

    context = {
        "db": db,
        "business_id": membership.business_id,
        "user_id": membership.user_id,
        "permissions": permissions,
    }

    result = await registry.execute_tool(
        name=payload.name,
        arguments=payload.arguments,
        context=context,
    )

    if result.get("status") == "error":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error"),
        )

    return result
