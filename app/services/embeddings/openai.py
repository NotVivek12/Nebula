import httpx

from app.core.logging import logger
from app.services.embeddings.base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI API wrapper implementing the BaseEmbeddingProvider contract."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.url = "https://api.openai.com/v1/embeddings"

    async def generate_embedding(self, text: str, model_name: str) -> list[float]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "input": text,
            "model": model_name,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(self.url, json=payload, headers=headers, timeout=20.0)
                response_data = response.json()

                if response.status_code >= 400:
                    logger.error(
                        "OpenAI embedding API returned error status",
                        status_code=response.status_code,
                        response=response_data,
                    )
                    response.raise_for_status()

                return list(response_data["data"][0]["embedding"])
            except Exception as e:
                logger.error("OpenAI embedding generation request failed", error=str(e))
                raise
