from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Abstract base class representing an executable capability/tool for the AI."""

    @property
    @abstractmethod
    def name(self) -> str:
        """The identifier name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """A description detailing what the tool does for LLM comprehension."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema dictionary describing the parameters required by the tool."""
        pass

    @property
    def required_permissions(self) -> list[str]:
        """List of user permission keys required to run this tool."""
        return []

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """Asynchronously executes the tool logic with arguments provided by the LLM."""
        pass
