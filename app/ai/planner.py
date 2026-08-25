from typing import Any


class AIPlanner:
    """Decides which tools to run based on customer intent and system schema."""

    def __init__(self) -> None:
        pass

    async def plan_tools(
        self,
        user_intent: str,
        available_tools: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Maps user intent to a sequence of tools to run."""
        # Structural placeholder
        return []
