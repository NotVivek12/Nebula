from typing import Any

import httpx

from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider


class OpenRouterLLMProvider(BaseLLMProvider):
    """OpenRouter API proxy wrapper implementing the BaseLLMProvider contract."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.url = "https://openrouter.ai/api/v1/chat/completions"

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
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://nebula.ai",
            "X-Title": "Nebula Platform Backend",
            "Content-Type": "application/json",
        }

        # Build message history payload (OpenRouter uses OpenAI-style format)
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_message})

        payload = {"model": model_name, "messages": messages, "temperature": temperature}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers, timeout=30.0)
                response_data = response.json()

                if response.status_code >= 400:
                    logger.error(
                        "OpenRouter API call returned error status",
                        status_code=response.status_code,
                        response=response_data,
                    )
                    response.raise_for_status()

                return str(response_data["choices"][0]["message"]["content"])
            except Exception as e:
                logger.error("OpenRouter API request failed", error=str(e))
                raise
