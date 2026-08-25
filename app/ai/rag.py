"""
Handles semantic knowledge retrieval (RAG) using Qdrant vector database.
"""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.integration import Integration
from app.services.embeddings.gemini import GeminiEmbeddingProvider
from app.services.embeddings.openai import OpenAIEmbeddingProvider
from app.services.vector_store.qdrant import QdrantVectorStore


class AIRagService:
    """Handles semantic knowledge retrieval for business documents (RAG)."""

    def __init__(self, db: AsyncSession, business_id: uuid.UUID) -> None:
        self.db = db
        self.business_id = business_id
        self.qdrant = QdrantVectorStore()

    async def _get_embedding_provider(self) -> tuple[Any, str] | None:
        """Resolves the active embedding provider and model name for this tenant."""
        query = select(Integration).where(
            Integration.business_id == self.business_id,
            Integration.is_active.is_(True),
            Integration.provider.in_(["openai", "gemini"]),
        )
        res = await self.db.execute(query)
        integration = res.scalar_one_or_none()

        if integration:
            api_key = integration.credentials.get("api_key")
            if not api_key:
                return None
            if integration.provider == "openai":
                return OpenAIEmbeddingProvider(str(api_key)), "text-embedding-3-small"
            else:
                return GeminiEmbeddingProvider(str(api_key)), "text-embedding-004"
                
        # Fallback to global settings if no integration is configured
        if settings.OPENAI_API_KEY:
            return OpenAIEmbeddingProvider(settings.OPENAI_API_KEY), "text-embedding-3-small"
        elif settings.GEMINI_API_KEY:
            return GeminiEmbeddingProvider(settings.GEMINI_API_KEY), "text-embedding-004"
            
        return None

    async def query_knowledge(self, query_text: str, limit: int = 5) -> list[str]:
        """
        Queries knowledge chunks belonging to the business tenant using semantic vector search.
        Falls back to empty list if no embedding provider is configured.
        """
        if not query_text.strip():
            return []
            
        provider_info = await self._get_embedding_provider()
        if not provider_info:
            logger.warning("No embedding provider available for RAG", business_id=str(self.business_id))
            return []
            
        provider, model_name = provider_info

        try:
            # 1. Embed the query text
            query_vector = await provider.generate_embedding(query_text, model_name=model_name)

            # 2. Search Qdrant with tenant isolation filter
            results = await self.qdrant.search_points(
                collection_name="knowledge_chunks",
                vector=query_vector,
                limit=limit,
                filter_metadata={"business_id": str(self.business_id)},
            )

            # 3. Extract payload text content
            chunks = []
            for hit in results:
                payload = hit.get("payload", {})
                content = payload.get("content")
                if content:
                    chunks.append(content)
                    
            logger.info("RAG query successful", business_id=str(self.business_id), chunks_found=len(chunks))
            return chunks

        except Exception as e:
            logger.error("RAG query failed", error=str(e), business_id=str(self.business_id))
            return []
