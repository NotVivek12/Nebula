import uuid

from sqlalchemy import ARRAY, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class KnowledgeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing a source file uploaded for the knowledge base."""

    __tablename__ = "knowledge_documents"

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)  # pdf, docx, txt, csv, md
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    business_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    chunks: Mapped[list["KnowledgeChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing a parsed chunk of a knowledge base document."""

    __tablename__ = "knowledge_chunks"

    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    custom_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    document: Mapped["KnowledgeDocument"] = relationship(back_populates="chunks")
    embeddings: Mapped[list["Embedding"]] = relationship(
        back_populates="chunk", cascade="all, delete-orphan"
    )


class Embedding(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Model representing vector embedding of a text chunk."""

    __tablename__ = "embeddings"

    # PostgreSQL ARRAY of float is very lightweight and portable.
    # If the database deployment includes pgvector, this can easily be migrated to vector type.
    vector: Mapped[list[float]] = mapped_column(ARRAY(Float), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), default="text-embedding-3-small", nullable=False)

    chunk_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("knowledge_chunks.id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    chunk: Mapped["KnowledgeChunk"] = relationship(back_populates="embeddings")
