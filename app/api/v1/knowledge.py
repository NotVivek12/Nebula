import uuid
from typing import Any

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authz import RequirePermission
from app.db.session import get_db
from app.models.business_user import BusinessUser
from app.models.integration import Integration
from app.models.knowledge import Embedding, KnowledgeChunk, KnowledgeDocument
from app.schemas.knowledge import KnowledgeSearchRequest
from app.services.embeddings.gemini import GeminiEmbeddingProvider
from app.services.embeddings.openai import OpenAIEmbeddingProvider
from app.services.knowledge.chunker import chunk_text
from app.services.knowledge.parser import parse_document, parse_website
from app.services.vector_store.qdrant import QdrantVectorStore

router = APIRouter()


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile | None = None,
    website_url: str | None = Form(None),
    membership: BusinessUser = Depends(RequirePermission("knowledge:write")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Uploads a document or scrapes a website, chunks, embeds, and indexes to Qdrant (requires knowledge:write)."""
    if not file and not website_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either an uploaded file or website_url.",
        )

    # 1. Resolve active embedding provider credentials for this tenant
    integration_query = select(Integration).where(
        Integration.business_id == membership.business_id,
        Integration.is_active.is_(True),
        Integration.provider.in_(["openai", "gemini"]),
    )
    res = await db.execute(integration_query)
    integration = res.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OpenAI or Gemini integration credentials found for this tenant business.",
        )

    api_key = integration.credentials.get("api_key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration credentials missing API key.",
        )

    if integration.provider == "openai":
        embedding_provider = OpenAIEmbeddingProvider(str(api_key))
        embedding_model = "text-embedding-3-small"
    else:
        embedding_provider = GeminiEmbeddingProvider(str(api_key))
        embedding_model = "text-embedding-004"

    # 2. Extract parsed text
    if file:
        content_bytes = await file.read()
        filename = file.filename or "uploaded_file"
        file_size = len(content_bytes)
        file_type = filename.split(".")[-1] if "." in filename else "txt"
        parsed_text = await parse_document(content_bytes, file_type)
    else:
        parsed_text = await parse_website(str(website_url))
        filename = str(website_url)
        file_size = len(parsed_text.encode("utf-8"))
        file_type = "website"

    # 3. Document Versioning calculation
    doc_query = (
        select(KnowledgeDocument)
        .where(KnowledgeDocument.business_id == membership.business_id)
        .where(KnowledgeDocument.filename == filename)
        .order_by(KnowledgeDocument.version.desc())
        .limit(1)
    )
    res = await db.execute(doc_query)
    existing_doc = res.scalar_one_or_none()
    new_version = (existing_doc.version + 1) if existing_doc else 1

    # 4. Save Knowledge Document metadata
    document = KnowledgeDocument(
        filename=filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=f"local://knowledge/{filename}" if file else filename,
        version=new_version,
        business_id=membership.business_id,
    )
    db.add(document)
    await db.flush()

    # 5. Chunk text content
    chunks = chunk_text(parsed_text)
    points = []

    for idx, chunk_content in enumerate(chunks):
        # Generate embedding vector
        vector = await embedding_provider.generate_embedding(chunk_content, model_name=embedding_model)

        # Save Knowledge Chunk metadata
        chunk = KnowledgeChunk(content=chunk_content, chunk_index=idx, document_id=document.id)
        db.add(chunk)
        await db.flush()

        # Save Relational Embedding
        emb = Embedding(vector=vector, model_name=embedding_model, chunk_id=chunk.id)
        db.add(emb)

        # Build Qdrant Vector Point payload
        points.append(
            {
                "id": str(uuid.uuid4()),
                "vector": vector,
                "payload": {
                    "business_id": str(membership.business_id),
                    "document_id": str(document.id),
                    "chunk_id": str(chunk.id),
                    "version": new_version,
                    "content": chunk_content,
                },
            }
        )

    # 6. Index vectors to Qdrant REST service
    try:
        qdrant_store = QdrantVectorStore()
        await qdrant_store.upsert_points("knowledge_chunks", points)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upsert vector indexes: {e}",
        )

    return {
        "status": "success",
        "document_id": str(document.id),
        "filename": filename,
        "version": new_version,
        "chunks_created": len(chunks),
    }


@router.post("/search")
async def search_knowledge(
    payload: KnowledgeSearchRequest,
    membership: BusinessUser = Depends(RequirePermission("knowledge:read")),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Performs semantic similarity search against indexed knowledge base (requires knowledge:read)."""
    # 1. Resolve active embedding provider credentials for this tenant
    integration_query = select(Integration).where(
        Integration.business_id == membership.business_id,
        Integration.is_active.is_(True),
        Integration.provider.in_(["openai", "gemini"]),
    )
    res = await db.execute(integration_query)
    integration = res.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OpenAI or Gemini integration credentials found for this tenant business.",
        )

    api_key = integration.credentials.get("api_key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Integration credentials missing API key.",
        )

    if integration.provider == "openai":
        embedding_provider = OpenAIEmbeddingProvider(str(api_key))
        embedding_model = "text-embedding-3-small"
    else:
        embedding_provider = GeminiEmbeddingProvider(str(api_key))
        embedding_model = "text-embedding-004"

    # 2. Generate vector embedding for the query
    try:
        query_vector = await embedding_provider.generate_embedding(payload.query, model_name=embedding_model)
    except Exception as e:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to embed query: {e}",
        )

    # 3. Query Qdrant with Business Isolation metadata filters
    try:
        qdrant_store = QdrantVectorStore()
        filter_metadata = {"business_id": str(membership.business_id)}
        results = await qdrant_store.search_points(
            collection_name="knowledge_chunks",
            vector=query_vector,
            limit=payload.limit,
            filter_metadata=filter_metadata,
        )
    except Exception as e:
        raise HTTPException(  # noqa: B904
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Semantic search execution failed: {e}",
        )

    # 4. Map and return response logs
    response_items = []
    for r in results:
        payload_data = r.get("payload", {})
        response_items.append(
            {
                "chunk_id": payload_data.get("chunk_id"),
                "document_id": payload_data.get("document_id"),
                "content": payload_data.get("content", ""),
                "score": r.get("score", 0.0),
            }
        )

    return response_items
