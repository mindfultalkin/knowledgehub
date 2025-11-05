"""
SQLAlchemy models for Knowledge Hub metadata database
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, 
    Float, JSON, ForeignKey, Index, BigInteger, Enum
)
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


# ============================================================
# ENUMS
# ============================================================

class ContentType(str, enum.Enum):
    TEMPLATE = "template"
    CLASS = "class"
    RESOURCE = "resource"
    CASE_LAW = "case_law"
    VIDEO = "video"
    OTHER = "other"


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskType(str, enum.Enum):
    EXTRACT_TEXT = "extract_text"
    GENERATE_THUMBNAIL = "generate_thumbnail"
    AI_TAGGING = "ai_tagging"
    CREATE_EMBEDDING = "create_embedding"


# ============================================================
# PRACTICE HIERARCHY MODELS
# ============================================================

class PracticeArea(Base):
    """
    Top-level practice areas (e.g., Employment Law, Corporate Law)
    """
    __tablename__ = "practice_areas"
    
    practice_area_id = Column(Integer, primary_key=True, autoincrement=True)
    practice_area_name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    responsible_partner = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sub_practice_areas = relationship("SubPracticeArea", back_populates="practice_area", cascade="all, delete-orphan")


class SubPracticeArea(Base):
    """
    Sub-practice areas (e.g., Employment Contracts, POSH Policy)
    """
    __tablename__ = "sub_practice_areas"
    
    sub_practice_id = Column(Integer, primary_key=True, autoincrement=True)
    practice_area_id = Column(Integer, ForeignKey("practice_areas.practice_area_id", ondelete="CASCADE"), nullable=False)
    sub_practice_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    practice_area = relationship("PracticeArea", back_populates="sub_practice_areas")
    documents = relationship("Document", back_populates="sub_practice_area")
    
    __table_args__ = (
        Index('idx_practice_area', 'practice_area_id'),
    )


# ============================================================
# DOCUMENT METADATA MODEL
# ============================================================

class Document(Base):
    """
    Main document metadata table - stores info about each file
    """
    __tablename__ = "documents"
    
    # Primary identifiers
    id = Column(String(255), primary_key=True)  # Google Drive file ID
    drive_file_id = Column(String(255), unique=True, nullable=False, index=True)
    
    # Basic metadata
    title = Column(String(500), nullable=False)
    mime_type = Column(String(255), nullable=True)
    file_format = Column(String(50), nullable=True)  # .pdf, .docx, etc.
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
    file_url = Column(Text, nullable=True)  # Google Drive web view link
    thumbnail_link = Column(Text, nullable=True)
    icon_link = Column(Text, nullable=True)
    
    # Derived data paths (local storage)
    derived_text_path = Column(String(500), nullable=True)
    derived_thumbnail_path = Column(String(500), nullable=True)
    
    # Version control
    version_number = Column(Integer, default=1)
    checksum = Column(String(64), nullable=True)  # MD5 or SHA256
    
    # Status and lifecycle
    status = Column(String(50), default="active")  # active, archived, deleted
    effective_date = Column(DateTime, nullable=True)
    review_cycle_days = Column(Integer, nullable=True)
    
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
    )


# ============================================================
# DOCUMENT CHUNKS (for NLP search)
# ============================================================

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


# ============================================================
# TAGS AND TAXONOMY
# ============================================================

class Tag(Base):
    """
    Tag taxonomy - hierarchical tag structure
    """
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    category = Column(String(100), nullable=True)  # e.g., "legal_area", "document_type"
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
    confidence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    source = Column(String(50), nullable=True)  # 'ml', 'rule', 'user'
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="document_tags")
    tag = relationship("Tag", back_populates="document_tags")
    
    __table_args__ = (
        Index('idx_document_tag', 'document_id', 'tag_id'),
        Index('idx_tag_confidence', 'tag_id', 'confidence_score'),
    )


# ============================================================
# VECTOR EMBEDDINGS
# ============================================================

class VectorEmbedding(Base):
    """
    Store vector embeddings for semantic search
    """
    __tablename__ = "vector_embeddings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_id = Column(Integer, ForeignKey("document_chunks.id", ondelete="CASCADE"), nullable=True)
    embedding = Column(JSON, nullable=False)  # Store as JSON array
    model_name = Column(String(100), nullable=True)  # e.g., "sentence-transformers/all-MiniLM-L6-v2"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="embeddings")
    
    __table_args__ = (
        Index('idx_document_embedding', 'document_id'),
    )


# ============================================================
# ACCESS CONTROL
# ============================================================

class AccessControl(Base):
    """
    Document-level access control
    """
    __tablename__ = "access_control"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    principal_id = Column(String(255), nullable=False)  # user email or team id
    principal_type = Column(String(50), nullable=False)  # 'user' or 'team'
    permission = Column(String(50), nullable=False)  # 'read', 'write', 'share'
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="access_controls")
    
    __table_args__ = (
        Index('idx_document_principal', 'document_id', 'principal_id'),
        Index('idx_principal', 'principal_id'),
    )


# ============================================================
# PROCESSING QUEUE
# ============================================================

class ProcessingQueue(Base):
    """
    Queue for background processing tasks
    """
    __tablename__ = "processing_queue"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    priority = Column(Integer, default=5)  # 1 = highest, 10 = lowest
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_status_priority', 'status', 'priority'),
        Index('idx_document_task', 'document_id', 'task_type'),
    )


# ============================================================
# SYNC CHECKPOINT
# ============================================================

class SyncCheckpoint(Base):
    """
    Track sync progress with Google Drive
    """
    __tablename__ = "sync_checkpoints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False)  # 'google_drive'
    last_sync_time = Column(DateTime, nullable=False)
    page_token = Column(String(500), nullable=True)
    files_processed = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    status = Column(String(50), default="completed")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_source_time', 'source', 'last_sync_time'),
    )
