"""
Access control models
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class AccessControl(Base):
    """
    Document-level access control
    """
    __tablename__ = "access_control"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    principal_id = Column(String(255), nullable=False)
    principal_type = Column(String(50), nullable=False)
    permission = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Relationships
    document = relationship("Document", back_populates="access_controls")
    
    __table_args__ = (
        Index('idx_document_principal', 'document_id', 'principal_id'),
        Index('idx_principal', 'principal_id'),
    )