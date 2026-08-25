from typing import Any

import httpx

from app.core.logging import logger
from app.services.llm.base import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini API wrapper implementing the BaseLLMProvider contract."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def generate_response(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, str]],
        user_message: str,
        model_name: str,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> str:
        # Standard models format: models/gemini-1.5-pro
        model = model_name if "/" in model_name else f"models/{model_name}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:generateContent?key={self.api_key}"

        # Map role objects: Gemini expects 'model' instead of 'assistant'
        contents = []
        for msg in conversation_history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["content"]}]})

        contents.append({"role": "user", "parts": [{"text": user_message}]})

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }

        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=30.0)
                response_data = response.json()

                if response.status_code >= 400:
                    logger.error(
                        "Gemini API call returned error status",
                        status_code=response.status_code,
                        response=response_data,
                    )
                    response.raise_for_status()

                return str(response_data["candidates"][0]["content"]["parts"][0]["text"])
            except Exception as e:
                logger.error("Gemini API request failed", error=str(e))
                raise
