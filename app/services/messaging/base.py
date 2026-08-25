from abc import ABC, abstractmethod
from typing import Any


class BaseMessagingProvider(ABC):
    """Abstract base class establishing the contract for all messaging channel providers."""

    @abstractmethod
    async def send_text(self, to: str, text: str, **kwargs: Any) -> dict[str, Any]:
        """Sends a plain text message to a recipient."""
        pass

    @abstractmethod
    async def send_image(
        self, to: str, image_url: str, caption: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Sends an image file with an optional text caption."""
        pass

    @abstractmethod
    async def send_document(
        self, to: str, document_url: str, filename: str | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Sends a document file with an optional descriptive name."""
        pass

    @abstractmethod
    async def send_interactive_buttons(
        self, to: str, body_text: str, buttons: list[dict[str, str]], **kwargs: Any
    ) -> dict[str, Any]:
        """Sends an interactive message containing click response buttons."""
        pass

    @abstractmethod
    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str,
        components: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Sends a pre-approved message template (useful for Meta notifications)."""
        pass
