"""
Clause-related database models
"""
from sqlalchemy import Column, Integer, String, Text, TIMESTAMP, ForeignKey
from sqlalchemy.sql import func
from database import Base


class DocumentClause(Base):
    """Extracted clauses from documents (temporary cache)"""
    __tablename__ = 'document_clauses'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(255), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False)
    clause_number = Column(Integer, nullable=False)
    clause_title = Column(String(500), nullable=False)
    clause_content = Column(Text, nullable=False)
    section_number = Column(String(50))
    extracted_at = Column(TIMESTAMP, server_default=func.now())


class ClauseLibrary(Base):
    """Saved clauses library (permanent storage)"""
    __tablename__ = 'clause_library'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    clause_title = Column(String(500), nullable=False)
    clause_content = Column(Text, nullable=False)
    section_number = Column(String(50))
    source_document_id = Column(String(255), ForeignKey('documents.id', ondelete='SET NULL'))
    source_document_name = Column(String(500))
    category = Column(String(100))
    saved_by = Column(String(255))
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
