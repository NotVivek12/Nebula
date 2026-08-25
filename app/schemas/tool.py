from typing import Any

from pydantic import BaseModel


class ToolExecuteRequest(BaseModel):
    """Request schema to execute a tool plugin."""

    name: str  # The tool identifier name (e.g., "create_lead", "send_email")
    arguments: dict[str, Any]  # Key-value arguments matching parameters JSON schema
