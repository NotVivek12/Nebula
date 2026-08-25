from abc import ABC, abstractmethod
from typing import Any


class BaseIntegrationConnector(ABC):
    """Abstract interface defining standard operations for third-party service integration connectors."""

    @abstractmethod
    async def authorize(self, credentials: dict[str, Any]) -> dict[str, Any]:
        """Validates or refreshes authentication credentials (OAuth/API keys)."""
        pass

    @abstractmethod
    async def test_connection(self, credentials: dict[str, Any]) -> bool:
        """Tests connectivity to the external service backend."""
        pass

    @abstractmethod
    async def run_action(
        self, credentials: dict[str, Any], action_name: str, payload: dict[str, Any]
    ) -> Any:
        """Executes a reusable action/service workflow against the connector."""
        pass
