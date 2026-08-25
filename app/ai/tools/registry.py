import time
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.tools.base import Tool
from app.ai.tools.email import SendEmailTool
from app.ai.tools.http import HTTPRequestTool
from app.ai.tools.lead import CreateLeadTool
from app.core.logging import logger
from app.models.audit import AuditLog


class ToolRegistry:
    """Centralized Tool registry managing plugin registration, discovery, validation, and execution."""

    def __init__(self) -> None:
        self.tools: dict[str, Tool] = {}
        # Register default plugin tools
        self.register(CreateLeadTool())
        self.register(SendEmailTool())
        self.register(HTTPRequestTool())

    def register(self, tool: Tool) -> None:
        """Registers a tool plugin."""
        self.tools[tool.name] = tool
        logger.info("Registered AI tool plugin", name=tool.name)

    def get_tool(self, name: str) -> Tool | None:
        """Retrieves a registered tool by name."""
        return self.tools.get(name)

    def list_tools(self, user_permissions: list[str] | None = None) -> list[dict[str, Any]]:
        """Lists registered tools.

        If user_permissions are provided, filters to return only tools the user has access to.
        """
        discovered = []
        for tool in self.tools.values():
            # Check permissions if filtering is requested
            if user_permissions is not None:
                has_access = all(p in user_permissions for p in tool.required_permissions)
                if not has_access:
                    continue

            discovered.append(
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                    "required_permissions": tool.required_permissions,
                }
            )
        return discovered

    async def execute_tool(
        self,
        name: str,
        arguments: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validates parameters, verifies permissions, executes tool logic, and logs database audits."""
        start_time = time.time()
        tool = self.get_tool(name)

        if not tool:
            return {"status": "error", "error": f"Tool '{name}' not found in registry."}

        db: AsyncSession = context.get("db")
        business_id: uuid.UUID = context.get("business_id")
        user_id: uuid.UUID = context.get("user_id")
        user_permissions: list[str] = context.get("permissions", [])

        # 1. Verify permissions (RBAC)
        has_access = all(p in user_permissions for p in tool.required_permissions)
        if not has_access:
            logger.warn(
                "Access denied for tool execution",
                tool=name,
                business_id=str(business_id),
                user_id=str(user_id),
            )
            return {
                "status": "error",
                "error": f"Permission Denied. Tool '{name}' requires: {tool.required_permissions}",
            }

        # 2. Validate input parameters against required list
        schema = tool.parameters
        required_fields = schema.get("required", [])
        missing = [f for f in required_fields if f not in arguments]
        if missing:
            return {
                "status": "error",
                "error": f"Missing required arguments for tool '{name}': {missing}",
            }

        # 3. Add system context elements to execution arguments
        exec_args = dict(arguments)
        if db:
            exec_args["db"] = db
        if business_id:
            exec_args["business_id"] = business_id

        # 4. Safely execute tool plugin
        audit_details = {
            "tool": name,
            "arguments": arguments,
            "latency_seconds": 0.0,
        }
        try:
            result = await tool.execute(**exec_args)
            latency = time.time() - start_time
            audit_details["latency_seconds"] = round(latency, 3)
            audit_details["status"] = "success"

            # Create DB Audit Log entry
            if db and business_id:
                audit = AuditLog(
                    action=f"tool_exec_{name}",
                    details=audit_details,
                    business_id=business_id,
                    user_id=user_id,
                )
                db.add(audit)
                await db.commit()

            return {"status": "success", "result": result}

        except Exception as e:
            latency = time.time() - start_time
            audit_details["latency_seconds"] = round(latency, 3)
            audit_details["status"] = "failed"
            audit_details["error"] = str(e)

            # Log execution failure
            logger.error("Tool execution failed", tool=name, error=str(e))

            if db and business_id:
                try:
                    audit = AuditLog(
                        action=f"tool_exec_fail_{name}",
                        details=audit_details,
                        business_id=business_id,
                        user_id=user_id,
                    )
                    db.add(audit)
                    await db.commit()
                except Exception:
                    pass

            return {"status": "error", "error": f"Tool execution failed: {e}"}
