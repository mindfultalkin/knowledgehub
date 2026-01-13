"""
Document metadata models
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    Float, JSON, ForeignKey, Index, BigInteger, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


class ContentType(str, enum.Enum):
    TEMPLATE = "template"
    CLAUSE_SET = "clause_set"
    PRACTICE_NOTE = "practice_note"
    KNOWLEDGE_MATERIAL = "knowledge_material"
    CLASS = "class"
    RESOURCE = "resource"
    CASE_LAW = "case_law"
    VIDEO = "video"
    OTHER = "other"


class Document(Base):
    """
    Main document metadata table - stores info about each file
    """
    __tablename__ = "documents"
    
    # Primary identifiers
    id = Column(String(255), primary_key=True)  # Google Drive file ID
    drive_file_id = Column(String(255), unique=True, nullable=False, index=True)
    
    account_email = Column(String(255), nullable=True, index=True)
    account_id = Column(String(255), nullable=True, index=True)
    
    # Basic metadata
    title = Column(String(500), nullable=False)
    mime_type = Column(String(255), nullable=True)
    file_format = Column(String(50), nullable=True)
    size_bytes = Column(BigInteger, nullable=True)
    
    # Content metadata
    content_type = Column(Enum(ContentType), nullable=True)
    description = Column(Text, nullable=True)
    language = Column(String(10), default="en")
    
    # Practice area classification
    sub_practice_id = Column(Integer, ForeignKey("sub_practice_areas.sub_practice_id", ondelete="SET NULL"), nullable=True)
    
    # Ownership and permissions
    owner_email = Column(String(255), nullable=True)
    owner_name = Column(String(255), nullable=True)
    
    # URLs and links
    file_url = Column(Text, nullable=True)
    thumbnail_link = Column(Text, nullable=True)
    icon_link = Column(Text, nullable=True)
    
    # Derived data paths (local storage)
    derived_text_path = Column(String(500), nullable=True)
    derived_thumbnail_path = Column(String(500), nullable=True)
    
    # Version control
    version_number = Column(Integer, default=1)
    checksum = Column(String(64), nullable=True)
    
    # Status and lifecycle
    status = Column(String(50), default="active")
    effective_date = Column(DateTime, nullable=True)
    review_cycle_days = Column(Integer, nullable=True)
    
    # Workflow & Knowledge Hub classification
    workflow_status = Column(String(50), nullable=True)
    bucket = Column(String(50), nullable=True)
    certified_by = Column(String(255), nullable=True)
    certified_at = Column(DateTime, nullable=True)
    variant = Column(String(100), nullable=True)
    
    # Legal metadata
    jurisdiction = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=True)
    modified_at = Column(DateTime, nullable=True)
    last_indexed_at = Column(DateTime, nullable=True)
    db_created_at = Column(DateTime, default=datetime.utcnow)
    db_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sub_practice_area = relationship("SubPracticeArea", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    document_tags = relationship("DocumentTag", back_populates="document", cascade="all, delete-orphan")
    embeddings = relationship("VectorEmbedding", back_populates="document", cascade="all, delete-orphan")
    access_controls = relationship("AccessControl", back_populates="document", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_mime_type', 'mime_type'),
        Index('idx_owner', 'owner_email'),
        Index('idx_status', 'status'),
        Index('idx_modified', 'modified_at'),
        Index('idx_sub_practice', 'sub_practice_id'),
        Index('idx_workflow_bucket', 'workflow_status', 'bucket'),
        Index('idx_content_type', 'content_type'),
        Index('idx_templates', 'content_type', 'workflow_status', 'bucket'),
    )


class DocumentChunk(Base):
    """
    Document chunks for improved NLP search
    Large documents are split into chunks for better semantic search
    """
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    text = Column(Text, nullable=False)
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")
    
    __table_args__ = (
        Index('idx_document_chunk', 'document_id', 'chunk_index'),
    )