"""
Processing queue models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from database import Base


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


class ProcessingQueue(Base):
    """
    Queue for background processing tasks
    """
    __tablename__ = "processing_queue"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    task_type = Column(Enum(TaskType), nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    priority = Column(Integer, default=5)
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