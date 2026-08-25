import httpx

from app.core.logging import logger
from app.services.embeddings.base import BaseEmbeddingProvider


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    """Google Gemini API wrapper implementing the BaseEmbeddingProvider contract."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def generate_embedding(self, text: str, model_name: str) -> list[float]:
        # Gemini model formatting: models/text-embedding-004
        model = model_name if "/" in model_name else f"models/{model_name}"
        url = f"https://generativelanguage.googleapis.com/v1beta/{model}:embedContent?key={self.api_key}"

        payload = {
            "content": {
                "parts": [{"text": text}]
            }
        }
        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=headers, timeout=20.0)
                response_data = response.json()

                if response.status_code >= 400:
                    logger.error(
                        "Gemini embedding API returned error status",
                        status_code=response.status_code,
                        response=response_data,
                    )
                    response.raise_for_status()

                return list(response_data["embedding"]["values"])
            except Exception as e:
                logger.error("Gemini embedding generation request failed", error=str(e))
                raise
