from abc import ABC, abstractmethod
from typing import Any


class BaseLLMProvider(ABC):
    """Abstract interface defining the contract for all Large Language Model (LLM) providers."""

    @abstractmethod
    async def generate_response(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, str]],
        user_message: str,
        model_name: str,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """Asynchronously executes prompt payload requests against LLM endpoints.

        Args:
            system_prompt: Base rules guiding the model behavior.
            conversation_history: Context logs formatting chat histories as {"role": "user"/"assistant", "content": "..."}.
            user_message: Active query input.
            model_name: Specific model identifier.
            temperature: Randomness control value.

        Returns:
            The generated response content string.
        """
        pass
