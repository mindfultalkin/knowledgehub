"""
Vector embedding models
"""
from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class VectorEmbedding(Base):
    """
    Store vector embeddings for semantic search
    """
    __tablename__ = "vector_embeddings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=True)
    embedding = Column(JSON, nullable=False)
    model_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="embeddings")
    
    __table_args__ = (
        Index('idx_document_embedding', 'document_id'),
    )