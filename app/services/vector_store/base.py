from abc import ABC, abstractmethod
from typing import Any


class BaseVectorStore(ABC):
    """Abstract interface defining the contract for interacting with Vector Databases."""

    @abstractmethod
    async def upsert_points(self, collection_name: str, points: list[dict[str, Any]]) -> None:
        """Asynchronously upserts vector points with payloads to a collection."""
        pass

    @abstractmethod
    async def search_points(
        self,
        collection_name: str,
        vector: list[float],
        limit: int,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Asynchronously queries similar vectors from a collection, applying filters."""
        pass
