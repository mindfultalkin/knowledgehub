"""
Practice hierarchy models
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


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