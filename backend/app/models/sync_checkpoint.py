"""
Sync checkpoint models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Index
from datetime import datetime

from database import Base


class SyncCheckpoint(Base):
    """
    Track sync progress with Google Drive
    """
    __tablename__ = "sync_checkpoints"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(100), nullable=False)
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