"""
Tag and taxonomy models
"""
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Tag(Base):
    """
    Tag taxonomy - hierarchical tag structure
    """
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=True)
    parent_id = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)
    description = Column(Text, nullable=True)
    synonym_of = Column(Integer, ForeignKey("tags.id", ondelete="SET NULL"), nullable=True)
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Self-referential relationships
    children = relationship("Tag", remote_side=[parent_id], foreign_keys=[parent_id])
    document_tags = relationship("DocumentTag", back_populates="tag")
    
    __table_args__ = (
        Index('idx_category', 'category'),
    )


class DocumentTag(Base):
    """
    Many-to-many relationship between documents and tags
    Includes confidence score and source
    """
    __tablename__ = "document_tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False)
    confidence_score = Column(Float, nullable=True)
    source = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="document_tags")
    tag = relationship("Tag", back_populates="document_tags")
    
    __table_args__ = (
        Index('idx_document_tag', 'document_id', 'tag_id'),
        Index('idx_tag_confidence', 'tag_id', 'confidence_score'),
    )