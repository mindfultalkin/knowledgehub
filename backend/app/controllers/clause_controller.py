"""
Clause extraction and library controllers
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel
from sqlalchemy import text

# Import models and services
from database import get_db
from app.models.document import Document
from app.models.clause import DocumentClause, ClauseLibrary
from app.services.clause_extractor_service import ClauseExtractor
from app.services.content_extractor_service import UniversalContentExtractor
from app.services.google_drive_service import GoogleDriveClient
from app.dependencies import get_drive_client, get_current_user_email

router = APIRouter()

# Initialize Google Drive client
try:
    drive_client = GoogleDriveClient()
except Exception as e:
    print(f"⚠️ Warning: Could not initialize drive client: {e}")
    drive_client = None

# ==================== PYDANTIC MODELS ====================

class SaveClauseRequest(BaseModel):
    document_id: str
    clause_number: int

class ClauseFileResponse(BaseModel):
    id: str
    title: str
    mime_type: str
    modified_at: str
    file_url: str
    owner_name: str

class ClauseFilesResponse(BaseModel):
    clause_title: str
    clause_content: str
    files: List[ClauseFileResponse]

class ClauseLibraryResponse(BaseModel):
    id: int
    title: str
    section_number: str
    content_preview: str
    source_document: str
    saved_by: str
    created_at: str

class ClauseLibraryListResponse(BaseModel):
    count: int
    clauses: List[ClauseLibraryResponse]

# ==================== HELPER FUNCTIONS ====================

def _get_document_by_any_id(db: Session, doc_id: str):
    """
    Find document by either internal ID or drive_file_id
    """
    # Try primary key first
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        return doc
    
    # Try drive_file_id
    doc = db.query(Document).filter(Document.drive_file_id == doc_id).first()
    if doc:
        return doc
    
    # If still not found, try with just the ID part (in case it has prefixes)
    if '_' in doc_id:
        parts = doc_id.split('_')
        if len(parts) > 1:
            # Try the last part as drive_file_id
            possible_id = parts[-1]
            doc = db.query(Document).filter(Document.drive_file_id.like(f'%{possible_id}%')).first()
            if doc:
                return doc
    
    return None

# ==================== CLAUSE ROUTES ====================

@router.get("/clauses/library/{clause_id}/files")
async def get_files_with_clause(clause_id: int, db: Session = Depends(get_db)):
    """
    Get all files that contain a specific clause from the library
    """
    try:
        print(f"🔍 Finding files with clause ID: {clause_id}")
        
        # Get the clause from library
        library_clause = db.query(ClauseLibrary).filter(
            ClauseLibrary.id == clause_id
        ).first()
        
        if not library_clause:
            raise HTTPException(status_code=404, detail="Clause not found in library")
        
        # Find all documents with this clause title (fuzzy search)
        matching_clauses = db.query(DocumentClause).filter(
            DocumentClause.clause_title.ilike(f"%{library_clause.clause_title}%")
        ).all()
        
        # Get unique document IDs
        doc_ids = list(set([clause.document_id for clause in matching_clauses]))
        
        if not doc_ids:
            return {
                "clause_title": library_clause.clause_title,
                "clause_content": library_clause.clause_content,
                "files": []
            }
        
        # Get document details
        documents = db.query(Document).filter(Document.id.in_(doc_ids)).all()
        
        # Create a mapping of document_id to clause for match type detection
        doc_to_clause = {}
        for clause in matching_clauses:
            doc_to_clause[clause.document_id] = clause
        
        files = []
        for doc in documents:
            # Determine match type: exact or similar
            clause_in_doc = doc_to_clause.get(doc.id)
            
            if clause_in_doc:
                # Case-insensitive exact match
                if clause_in_doc.clause_title.strip().lower() == library_clause.clause_title.strip().lower():
                    match_type = "exact"
                else:
                    match_type = "similar"
            else:
                match_type = "similar"
            
            files.append({
                "id": doc.id,
                "title": doc.title,
                "mime_type": doc.mime_type,
                "modified_at": doc.modified_at.isoformat() if doc.modified_at else None,
                "file_url": doc.file_url,
                "owner_name": doc.owner_name,
                "match_type": match_type  # ← ADD THIS
            })
        
        print(f"✅ Found {len(files)} files with this clause")
        
        return {
            "clause_title": library_clause.clause_title,
            "clause_content": library_clause.clause_content,
            "files": files
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clauses/check-saved/{document_id}/{clause_number}")
async def check_clause_saved(
    document_id: str,
    clause_number: int,
    db: Session = Depends(get_db)
):
    """
    Check if a specific clause is already saved in the library
    """
    try:
        print(f"🔍 Checking if clause {clause_number} from {document_id} is saved")
        
        # Get the clause from document_clauses table
        doc_clause = db.query(DocumentClause).filter(
            DocumentClause.document_id == document_id,
            DocumentClause.clause_number == clause_number
        ).first()
        
        if not doc_clause:
            print(f"❌ Clause not found in cache")
            return {"saved": False}
        
        # Check if it exists in clause_library
        existing = db.query(ClauseLibrary).filter(
            ClauseLibrary.source_document_id == document_id,
            ClauseLibrary.clause_title == doc_clause.clause_title
        ).first()
        
        if existing:
            print(f"✅ Clause already saved in library (ID: {existing.id})")
            return {
                "saved": True,
                "library_id": existing.id
            }
        else:
            print(f"ℹ️ Clause not saved yet")
            return {
                "saved": False,
                "library_id": None
            }
        
    except Exception as e:
        print(f"❌ Error checking saved status: {e}")
        import traceback
        print(traceback.format_exc())
        return {"saved": False}

@router.get("/clauses/library")
async def get_library_clauses(
    user_email: str = Query("public", description="Current user's email"),
    db: Session = Depends(get_db)
):
    try:
        print(f"🔍 Loading library for: {user_email}")
        
        if user_email == "public":
            print("⚠️ No user email - returning empty library")
            return {"count": 0, "clauses": []}
        
        clauses = db.query(ClauseLibrary).filter(
            ClauseLibrary.saved_by == user_email
        ).order_by(ClauseLibrary.created_at.desc()).all()
        
        clause_list = [
            {
                'id': c.id,
                'title': c.clause_title,
                'section_number': c.section_number,
                'content_preview': (c.clause_content[:200] + '...') if len(c.clause_content) > 200 else c.clause_content,
                'source_document': c.source_document_name or 'Unknown',
                'saved_by': c.saved_by,
                'created_at': c.created_at.isoformat() if c.created_at else None
            }
            for c in clauses
        ]
        
        print(f"✅ Found {len(clause_list)} clauses for {user_email}")
        return {"count": len(clause_list), "clauses": clause_list}
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"count": 0, "clauses": []}

@router.post("/documents/{file_id}/extract-clauses")
async def extract_clauses(
    file_id: str, 
    db: Session = Depends(get_db),
    drive_client: GoogleDriveClient = Depends(get_drive_client)  # Add dependency injection
):
    try:
        document = _get_document_by_any_id(db, file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        print(f"📄 Extracting clauses from: {document.title}")
        
        # Extract content using existing content extractor
        # FIX: Update the import path
        from app.services.content_extractor_service import UniversalContentExtractor
        content_extractor = UniversalContentExtractor(drive_client)
        content = content_extractor.extract_content(file_id, document.mime_type or '')
        
        if not content:
            return {
                "message": "No content found in document",
                "count": 0,
                "clauses": []
            }
        
        # Extract clauses from content
        from app.services.clause_extractor_service import ClauseExtractor  # Add import
        extractor = ClauseExtractor()
        clauses = extractor.extract_clauses_from_content(content)
        
        if not clauses:
            return {
                "message": "No clauses found",
                "count": 0,
                "clauses": []
            }
        
        # Clear old cached clauses for this document
        # FIX: Use document.id instead of file_id for consistency
        effective_document_id = document.id
        db.query(DocumentClause).filter(DocumentClause.document_id == effective_document_id).delete()
        db.commit()
        
        # Save to document_clauses table (temporary cache)
        for clause in clauses:
            doc_clause = DocumentClause(
                document_id=effective_document_id,
                clause_number=clause['clause_number'],
                clause_title=clause['title'],
                clause_content=clause['content'],
                section_number=clause.get('section_number', '')
            )
            db.add(doc_clause)
        
        db.commit()
        print(f"✅ Saved {len(clauses)} clauses to cache for document {effective_document_id}")
        
        # Return clause list for display
        clause_list = [
            {
                'clause_number': c['clause_number'],
                'section_number': c.get('section_number', str(c['clause_number'])),
                'title': c['title'],
                'content_preview': (c['content'][:100] + '...') if len(c['content']) > 100 else c['content']
            }
            for c in clauses
        ]
                
        return {
            "success": True,
            "message": f"Found {len(clauses)} clauses",
            "count": len(clauses),
            "clauses": clause_list,
            "document_id": effective_document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error extracting clauses: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Clause extraction failed: {str(e)}")
    
@router.get("/documents/{file_id}/clauses/{clause_number}")
async def get_clause_content(file_id: str, clause_number: int, db: Session = Depends(get_db)):
    """
    Get full content of a specific clause
    """
    try:
        clause = db.query(DocumentClause).filter(
            DocumentClause.document_id == file_id,
            DocumentClause.clause_number == clause_number
        ).first()
        
        if not clause:
            raise HTTPException(status_code=404, detail="Clause not found")
        
        return {
            "clause_number": clause.clause_number,
            "section_number": clause.section_number or str(clause.clause_number),
            "title": clause.clause_title,
            "content": clause.clause_content
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{file_id}/cached-clauses")
async def get_cached_clauses(file_id: str, db: Session = Depends(get_db)):
    """Get cached clauses for a document"""
    try:
        clauses = db.query(DocumentClause).filter(
            DocumentClause.document_id == file_id
        ).order_by(DocumentClause.clause_number).all()
        
        if not clauses:
            return {"clauses": []}
        
        return {
            "clauses": [
                {
                    "clause_number": clause.clause_number,
                    "section_number": clause.section_number,
                    "title": clause.clause_title,
                    "content": clause.clause_content or None
                }
                for clause in clauses
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clauses/save-to-library")
async def save_clause_to_library(
    request: SaveClauseRequest,
    user_email: str = Query(..., description="Current user's email"),  # ✅ REQUIRED
    db: Session = Depends(get_db)
):
    """
    Save a clause to the permanent library
    """
    try:
        document_id = request.document_id
        clause_number = request.clause_number
        
        print(f"💾 Saving clause {clause_number} from document {document_id}")
        
        # Get clause from temporary cache
        doc_clause = db.query(DocumentClause).filter(
            DocumentClause.document_id == document_id,
            DocumentClause.clause_number == clause_number
        ).first()
        
        if not doc_clause:
            print(f"❌ Clause not found in cache")
            raise HTTPException(status_code=404, detail="Clause not found in cache. Please extract clauses first.")
        
        # Get document info
        document = db.query(Document).filter(Document.id == document_id).first()
        
        # Check if already saved (avoid duplicates)
        existing = db.query(ClauseLibrary).filter(
            ClauseLibrary.source_document_id == document_id,
            ClauseLibrary.clause_title == doc_clause.clause_title
        ).first()
        
        if existing:
            print(f"ℹ️ Clause already exists in library: {existing.id}")
            return {
                "success": True,
                "message": "Clause already saved to library",
                "library_id": existing.id,
                "already_saved": True
            }
        
        # Save to library
        library_clause = ClauseLibrary(
            clause_title=doc_clause.clause_title,
            clause_content=doc_clause.clause_content,
            section_number=doc_clause.section_number,
            source_document_id=document_id,
            source_document_name=document.title if document else None,
            saved_by=user_email  # ✅ CURRENT USER!
        )
        
        db.add(library_clause)
        db.commit()
        db.refresh(library_clause)
        
        print(f"✅ Saved clause to library: ID {library_clause.id}")
        
        return {
            "success": True,
            "message": "Clause saved to library successfully",
            "library_id": library_clause.id,
            "already_saved": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error saving clause: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clauses/{clause_title}/similar-files")
async def find_similar_clauses(
    clause_title: str,
    current_file_id: str,
    db: Session = Depends(get_db)
):
    """
    Find other files that contain the same or similar clause title,
    including the full text (clause_content) for side-by-side comparison.
    """
    try:
        print(f"🔍 Searching for clauses similar to: {clause_title}")
        print(f"   Excluding current file: {current_file_id}")

        # Search for similar clause titles (case-insensitive, fuzzy matching)
        similar_clauses = db.query(DocumentClause).filter(
            DocumentClause.document_id != current_file_id,
            DocumentClause.clause_title.ilike(f"%{clause_title}%")
        ).all()

        print(f"   Found {len(similar_clauses)} similar clauses in database")

        if not similar_clauses:
            return {
                "found": False,
                "count": 0,
                "files": []
            }

        # Group by document and get file info, include clause_content
        files_dict = {}
        for clause in similar_clauses:
            doc_id = clause.document_id
            # Only use the first matching clause per document
            if doc_id not in files_dict:  
                # Get document info from database
                document = db.query(Document).filter(Document.id == doc_id).first()
                files_dict[doc_id] = {
                    "file_id": doc_id,
                    "file_name": document.title if document else "Unknown Document",
                    "clause_title": clause.clause_title,
                    "section_number": clause.section_number,
                    "clause_content": clause.clause_content,  # <<-- ADDED!
                    "match_type": "exact" if clause.clause_title.lower() == clause_title.lower() else "similar"
                }

        files_list = list(files_dict.values())

        print(f"✅ Returning {len(files_list)} files with similar clauses")

        return {
            "found": True,
            "count": len(files_list),
            "files": files_list
        }

    except Exception as e:
        print(f"❌ Error finding similar clauses: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))