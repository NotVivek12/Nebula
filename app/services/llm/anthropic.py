from typing import Any

import httpx

from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider


class AnthropicLLMProvider(BaseLLMProvider):
    """Anthropic Claude API wrapper implementing the BaseLLMProvider contract."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.url = "https://api.anthropic.com/v1/messages"

    async def generate_response(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, str]],
        user_message: str,
        model_name: str,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        # Anthropic processes messages excluding system role (handled as parameter)
        messages = list(conversation_history)
        messages.append({"role": "user", "content": user_message})

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "max_tokens": 4096,
            "temperature": temperature,
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers, timeout=30.0)
                response_data = response.json()

                if response.status_code >= 400:
                    logger.error(
                        "Anthropic API call returned error status",
                        status_code=response.status_code,
                        response=response_data,
                    )
                    response.raise_for_status()

                return str(response_data["content"][0]["text"])
            except Exception as e:
                logger.error("Anthropic API request failed", error=str(e))
                raise
