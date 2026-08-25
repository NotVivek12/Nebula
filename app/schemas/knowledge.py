import uuid

from pydantic import BaseModel


class KnowledgeSearchRequest(BaseModel):
    """Request schema for semantic similarity search."""

    query: str
    limit: int = 5


class KnowledgeSearchResponse(BaseModel):
    """Response schema representing a ranked retrieved knowledge chunk."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    content: str
    score: float
