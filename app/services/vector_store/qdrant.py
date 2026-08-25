from typing import Any

import httpx

from app.core.logging import logger
from app.services.vector_store.base import BaseVectorStore


class QdrantVectorStore(BaseVectorStore):
    """Qdrant Vector Database REST client implementing the BaseVectorStore contract."""

    def __init__(self, host: str = "http://localhost:6333") -> None:
        self.host = host.rstrip("/")

    async def _collection_exists(self, client: httpx.AsyncClient, collection_name: str) -> bool:
        """Checks if a collection exists in Qdrant."""
        url = f"{self.host}/collections/{collection_name}"
        try:
            response = await client.get(url, timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    async def _create_collection(self, client: httpx.AsyncClient, collection_name: str, size: int) -> None:
        """Creates a new collection with the given vector dimension using Cosine distance."""
        url = f"{self.host}/collections/{collection_name}"
        payload = {
            "vectors": {
                "size": size,
                "distance": "Cosine"
            }
        }
        response = await client.put(url, json=payload, timeout=10.0)
        if response.status_code >= 400:
            logger.error(
                "Failed to create Qdrant collection",
                collection=collection_name,
                response=response.json(),
            )
            response.raise_for_status()
        logger.info("Created Qdrant collection successfully", collection=collection_name, size=size)

    async def upsert_points(self, collection_name: str, points: list[dict[str, Any]]) -> None:
        if not points:
            return

        async with httpx.AsyncClient() as client:
            # 1. Ensure collection exists
            exists = await self._collection_exists(client, collection_name)
            if not exists:
                # Deduce vector dimension size from first point
                first_vector = points[0].get("vector", [])
                dimension_size = len(first_vector)
                if dimension_size == 0:
                    raise ValueError("Cannot deduce vector dimension from points payload")
                await self._create_collection(client, collection_name, dimension_size)

            # 2. Execute upsert points REST call
            url = f"{self.host}/collections/{collection_name}/points?wait=true"
            payload = {
                "points": points
            }
            try:
                response = await client.put(url, json=payload, timeout=20.0)
                if response.status_code >= 400:
                    logger.error(
                        "Qdrant points upsert failed",
                        collection=collection_name,
                        response=response.json(),
                    )
                    response.raise_for_status()
                logger.info("Upserted points to Qdrant successfully", collection=collection_name, count=len(points))
            except Exception as e:
                logger.error("Qdrant upsert request threw exception", error=str(e))
                raise

    async def search_points(
        self,
        collection_name: str,
        vector: list[float],
        limit: int,
        filter_metadata: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        url = f"{self.host}/collections/{collection_name}/points/search"

        # Build Qdrant search payload
        payload: dict[str, Any] = {
            "vector": vector,
            "limit": limit,
            "with_payload": True,
        }

        # Inject must matches filters if metadata parameters are specified
        if filter_metadata:
            must_filters = []
            for k, v in filter_metadata.items():
                must_filters.append({
                    "key": k,
                    "match": {"value": v}
                })
            payload["filter"] = {
                "must": must_filters
            }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, timeout=10.0)
                if response.status_code == 404:
                    # Collection doesn't exist yet, return empty list
                    logger.warn("Qdrant search collection not found", collection=collection_name)
                    return []
                elif response.status_code >= 400:
                    logger.error(
                        "Qdrant search query failed",
                        collection=collection_name,
                        response=response.json(),
                    )
                    response.raise_for_status()

                response_data = response.json()
                results = response_data.get("result", [])
                return list(results)
            except Exception as e:
                logger.error("Qdrant search request failed", error=str(e))
                raise
