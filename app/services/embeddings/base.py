from abc import ABC, abstractmethod


class BaseEmbeddingProvider(ABC):
    """Abstract interface defining the contract for generating vector text embeddings."""

    @abstractmethod
    async def generate_embedding(self, text: str, model_name: str) -> list[float]:
        """Asynchronously converts text into a float list vector representation."""
        pass
