"""
NVIDIA NIM LLM provider.

Uses the NVIDIA API (OpenAI-compatible) to access Nemotron and other NVIDIA-hosted models.
Default model: nvidia/llama-3.1-nemotron-70b-instruct

NVIDIA API is OpenAI-compatible — we use the openai SDK with a custom base_url.
API key is the NVIDIA_API_KEY from settings or from the business integration credentials.
"""

from typing import Any

from openai import AsyncOpenAI

from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider


class NvidiaNIMProvider(BaseLLMProvider):
    """
    LLM provider wrapping NVIDIA's NIM inference API.

    Supports all NVIDIA-hosted models including:
    - nvidia/llama-3.1-nemotron-70b-instruct
    - meta/llama-3.1-70b-instruct
    - mistralai/mixtral-8x22b-instruct-v0.1
    """

    def __init__(self, api_key: str, base_url: str | None = None) -> None:
        from app.core.config import settings  # noqa: PLC0415

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url or settings.NVIDIA_BASE_URL,
        )

    async def generate_response(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, str]],
        user_message: str,
        model_name: str = "nvidia/llama-3.1-nemotron-70b-instruct",
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        """
        Generates a response using NVIDIA NIM inference.

        The API is fully OpenAI-compatible. System prompt, history, and user
        message are assembled into the standard messages array.
        """
        messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = await self._client.chat.completions.create(
                model=model_name,
                messages=messages,  # type: ignore[arg-type]
                temperature=temperature,
                max_tokens=kwargs.get("max_tokens", 1024),
            )
            content = response.choices[0].message.content or ""
            logger.info(
                "NVIDIA NIM response generated",
                model=model_name,
                tokens_used=response.usage.total_tokens if response.usage else "unknown",
            )
            return content

        except Exception as exc:
            logger.error(
                "NVIDIA NIM API call failed",
                model=model_name,
                error=str(exc),
            )
            raise
