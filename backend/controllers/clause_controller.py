from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any
from pydantic import BaseModel

from database import get_db
from core.google_client import drive_client

from models.clauses import DocumentClause, ClauseLibrary, ClauseTag
from models.metadata import Document, Tag

from services.clause_extractor import ClauseExtractor
from services.risk_scoring import score_contract
from services.universal_content_extractor import UniversalContentExtractor

# Initialize router
router = APIRouter()


class SaveClauseRequest(BaseModel):
    document_id: str
    clause_number: int

class ClauseTagCreate(BaseModel):
    clause_id: int
    tag_name: str

class ClauseTagRemove(BaseModel):
    clause_id: int
    tag_id: int


# ==================== HELPERS ====================

def _get_document_by_any_id(db: Session, doc_id: str):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        return doc
    return db.query(Document).filter(Document.drive_file_id == doc_id).first()



#==================== CLAUSE EXTRACTION ROUTES ====================

@router.post("/documents/{file_id}/extract-clauses")
async def extract_clauses(file_id: str, db: Session = Depends(get_db)):
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        document = _get_document_by_any_id(db, file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        print(f"📄 Extracting clauses from: {document.title}")
        
        # Extract structured content
        content_extractor = UniversalContentExtractor(drive_client)

        blocks = content_extractor.extract_structured(
            file_id,
            document.mime_type or ''
        )

        if not blocks:
            return {
                "message": "No content found in document",
                "count": 0,
                "clauses": []
            }

        #  FIX: capture returned clauses
        extractor = ClauseExtractor()
        clauses = extractor.extract_clauses_from_blocks(blocks)

        if not clauses:
            return {
                "message": "No clauses found",
                "count": 0,
                "clauses": []
            }

        # Clear old cached clauses for this document
        db.query(DocumentClause).filter(
            DocumentClause.document_id == file_id
        ).delete()
        db.commit()

        # Save clauses to cache
        for clause in clauses:
            doc_clause = DocumentClause(
                document_id=file_id,
                clause_number=clause['clause_number'],
                clause_title=clause['title'],
                clause_content=clause['content'],
                section_number=clause.get('section_number', '')
            )
            db.add(doc_clause)

        db.commit()
        print(f" Saved {len(clauses)} clauses to cache")

        # Response for UI
        clause_list = [
            {
                'clause_number': c['clause_number'],
                'section_number': c.get('section_number', str(c['clause_number'])),
                'title': c['title']
            }
            for c in clauses
        ]

        return {
            "message": f"Found {len(clauses)} clauses",
            "count": len(clauses),
            "clauses": clause_list
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/{file_id}/refetch-clauses")
async def refetch_clauses(file_id: str, db: Session = Depends(get_db)):
    """
    Force re-extraction of clauses:
    - Deletes existing cached clauses
    - Extracts clauses again from source document
    """
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # 1. Fetch document (supports Drive ID or internal ID)
        document = _get_document_by_any_id(db, file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        print(f"Re-fetching clauses for document: {document.title}")

        # 2. Delete cached clauses
        deleted_count = db.query(DocumentClause).filter(
            DocumentClause.document_id == document.id
        ).delete()

        db.commit()
        print(f"Deleted {deleted_count} cached clauses")

        # 3. Extract structured content again
        content_extractor = UniversalContentExtractor(drive_client)
        blocks = content_extractor.extract_structured(
            document.drive_file_id or document.id,
            document.mime_type or ""
        )

        if not blocks:
            return {
                "message": "No content found during re-extraction",
                "deleted": deleted_count,
                "count": 0,
                "clauses": []
            }

        # 4. Extract clauses from content blocks
        extractor = ClauseExtractor()
        clauses = extractor.extract_clauses_from_blocks(blocks)

        if not clauses:
            return {
                "message": "No clauses found during re-extraction",
                "deleted": deleted_count,
                "count": 0,
                "clauses": []
            }

        # 5. Save fresh clauses
        for clause in clauses:
            db.add(DocumentClause(
                document_id=document.id,
                clause_number=clause["clause_number"],
                clause_title=clause["title"],
                clause_content=clause["content"],
                section_number=clause.get("section_number", "")
            ))

        db.commit()
        print(f"Saved {len(clauses)} fresh clauses")

        # 6. Return response for UI
        return {
            "message": "Clauses re-fetched successfully",
            "deleted": deleted_count,
            "count": len(clauses),
            "clauses": [
                {
                    "clause_number": c["clause_number"],
                    "section_number": c.get("section_number", str(c["clause_number"])),
                    "title": c["title"]
                }
                for c in clauses
            ]
        }

    except Exception as e:
        db.rollback()
        print(f"Refetch error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

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

# ============================================================
# CLAUSE EXTRACTION ENDPOINTS (CORRECT ORDER)
# ============================================================

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


# 1️⃣ MOST SPECIFIC ROUTE FIRST - Must come before generic routes
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


# 2️⃣ OTHER SPECIFIC ROUTES
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
        
        clause_list = []
        
        for clause in clauses:  # ← This variable is 'clause', not 'c'
            # Get tags for this clause
            clause_tags = db.query(ClauseTag, Tag).join(
                Tag, ClauseTag.tag_id == Tag.id
            ).filter(
                ClauseTag.clause_id == clause.id  # ← Changed from 'c.id' to 'clause.id'
            ).all()
            
            tags = [
                {
                    "id": tag.id,
                    "name": tag.name,
                    "category": tag.category
                }
                for _, tag in clause_tags
            ]
            
            clause_list.append({
                'id': clause.id,  # ← Changed from 'c.id' to 'clause.id'
                'title': clause.clause_title,  # ← Changed from 'c.clause_title'
                'section_number': clause.section_number,  # ← Changed from 'c.section_number'
                'content_preview': (clause.clause_content[:200] + '...') if len(clause.clause_content) > 200 else clause.clause_content,  # ← Changed from 'c.clause_content'
                'source_document': clause.source_document_name or 'Unknown',  # ← Changed from 'c.source_document_name'
                'saved_by': clause.saved_by,  # ← Changed from 'c.saved_by'
                'created_at': clause.created_at.isoformat() if clause.created_at else None,  # ← Changed from 'c.created_at'
                'tags': tags,
                'tag_count': len(tags)
            })
        
        print(f"✅ Found {len(clause_list)} clauses for {user_email}")
        return {"count": len(clause_list), "clauses": clause_list}
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"count": 0, "clauses": []}


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


#Contract Risk Scoring

@router.get("/contracts/{file_id}/risk-score")
async def risk_score(file_id: str, db: Session = Depends(get_db)):
    """
    Returns contract-level risk summary, per-clause risk, and missing clause checklist.
    """
    try:
        # Fetch all clauses for this document
        clauses = db.query(DocumentClause).filter(DocumentClause.document_id == file_id).all()
        clause_list = [
            {
                "clause_number": c.clause_number,
                "section_number": c.section_number,
                "title": c.clause_title,
                "content": c.clause_content,
            }
            for c in clauses
        ]
        return score_contract(clause_list)
    except Exception as e:
        print(f"❌ Risk scoring error: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# ==================== CLAUSE TAGS MANAGEMENT ====================

@router.post("/clauses/library/tags/add")
async def add_tag_to_clause(
    request: ClauseTagCreate,
    user_email: str = Query(..., description="Current user's email"),
    db: Session = Depends(get_db)
):
    """
    Add a tag to a saved clause in the library
    """
    try:
        print(f"🏷️ Adding tag '{request.tag_name}' to clause ID {request.clause_id}")
        
        # 1. Verify the clause exists and belongs to the user
        clause = db.query(ClauseLibrary).filter(
            ClauseLibrary.id == request.clause_id,
            ClauseLibrary.saved_by == user_email
        ).first()
        
        if not clause:
            raise HTTPException(
                status_code=404, 
                detail="Clause not found or you don't have permission"
            )
        
        # 2. Clean tag name
        tag_name = request.tag_name.strip()
        if not tag_name:
            raise HTTPException(status_code=400, detail="Tag name cannot be empty")
        
        # 3. Find or create the tag in master tags table
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            # Create new tag
            tag = Tag(
                name=tag_name,
                category="clause",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(tag)
            db.flush()  # Get the ID
            print(f"📝 Created new tag: {tag_name}")
        
        # 4. Check if tag is already linked to this clause
        existing_clause_tag = db.query(ClauseTag).filter(
            ClauseTag.clause_id == request.clause_id,
            ClauseTag.tag_id == tag.id
        ).first()
        
        if existing_clause_tag:
            return {
                "success": True,
                "message": f"Tag '{tag_name}' already exists on this clause",
                "already_exists": True
            }
        
        # 5. Create the clause_tag relationship
        clause_tag = ClauseTag(
            clause_id=request.clause_id,
            tag_id=tag.id,
            created_by=user_email,
            created_at=datetime.utcnow()
        )
        
        db.add(clause_tag)
        db.commit()
        
        print(f"✅ Tag '{tag_name}' added to clause '{clause.clause_title}'")
        
        return {
            "success": True,
            "message": f"Tag '{tag_name}' added to clause",
            "clause_id": request.clause_id,
            "tag_id": tag.id,
            "tag_name": tag_name,
            "already_exists": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error adding tag to clause: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/clauses/library/tags/remove")
async def remove_tag_from_clause(
    request: ClauseTagRemove,
    user_email: str = Query(..., description="Current user's email"),
    db: Session = Depends(get_db)
):
    """
    Remove a tag from a saved clause
    """
    try:
        print(f"🗑️ Removing tag ID {request.tag_id} from clause ID {request.clause_id}")
        
        # 1. Verify the clause exists and belongs to the user
        clause = db.query(ClauseLibrary).filter(
            ClauseLibrary.id == request.clause_id,
            ClauseLibrary.saved_by == user_email
        ).first()
        
        if not clause:
            raise HTTPException(
                status_code=404, 
                detail="Clause not found or you don't have permission"
            )
        
        # 2. Verify the tag exists
        tag = db.query(Tag).filter(Tag.id == request.tag_id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # 3. Find and remove the clause_tag relationship
        clause_tag = db.query(ClauseTag).filter(
            ClauseTag.clause_id == request.clause_id,
            ClauseTag.tag_id == request.tag_id
        ).first()
        
        if not clause_tag:
            return {
                "success": True,
                "message": "Tag was not associated with this clause",
                "already_removed": True
            }
        
        db.delete(clause_tag)
        db.commit()
        
        print(f"✅ Tag '{tag.name}' removed from clause '{clause.clause_title}'")
        
        return {
            "success": True,
            "message": f"Tag '{tag.name}' removed from clause",
            "clause_id": request.clause_id,
            "tag_id": request.tag_id,
            "already_removed": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ Error removing tag from clause: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clauses/library/{clause_id}/tags")
async def get_clause_tags(
    clause_id: int,
    user_email: str = Query(..., description="Current user's email"),
    db: Session = Depends(get_db)
):
    """
    Get all tags for a specific saved clause
    """
    try:
        print(f"🔍 Getting tags for clause ID {clause_id}")
        
        # Verify the clause exists and belongs to the user
        clause = db.query(ClauseLibrary).filter(
            ClauseLibrary.id == clause_id,
            ClauseLibrary.saved_by == user_email
        ).first()
        
        if not clause:
            raise HTTPException(
                status_code=404, 
                detail="Clause not found or you don't have permission"
            )
        
        # Get all tags for this clause
        clause_tags = db.query(ClauseTag, Tag).join(
            Tag, ClauseTag.tag_id == Tag.id
        ).filter(
            ClauseTag.clause_id == clause_id
        ).all()
        
        tags = [
            {
                "id": tag.id,
                "name": tag.name,
                "category": tag.category,
                "added_at": clause_tag.created_at.isoformat() if clause_tag.created_at else None,
                "added_by": clause_tag.created_by
            }
            for clause_tag, tag in clause_tags
        ]
        
        return {
            "clause_id": clause_id,
            "clause_title": clause.clause_title,
            "tags": tags,
            "count": len(tags)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error getting clause tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clauses/library/tags/all")
async def get_all_clause_tags(
    user_email: str = Query(..., description="Current user's email"),
    db: Session = Depends(get_db)
):
    """
    Get all tags used across all saved clauses (for filtering dropdown)
    """
    try:
        print(f"🔍 Getting all clause tags for user: {user_email}")
        
        # Get distinct tags used in user's clauses
        clause_tags = db.query(Tag).join(ClauseTag).join(ClauseLibrary).filter(
            ClauseLibrary.saved_by == user_email
        ).distinct().all()
        
        tags = [
            {
                "id": tag.id,
                "name": tag.name,
                "category": tag.category,
                "usage_count": db.query(ClauseTag).filter(ClauseTag.tag_id == tag.id).count()
            }
            for tag in clause_tags
        ]
        
        # Sort by usage count (most used first)
        tags.sort(key=lambda x: x["usage_count"], reverse=True)
        
        return {
            "tags": tags,
            "count": len(tags),
            "user_email": user_email
        }
        
    except Exception as e:
        print(f"❌ Error getting all clause tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clauses/library/filter/by-tag")
async def filter_clauses_by_tag(
    tag_id: int = Query(..., description="Tag ID to filter by"),
    user_email: str = Query(..., description="Current user's email"),
    db: Session = Depends(get_db)
):
    """
    Filter saved clauses by a specific tag
    """
    try:
        print(f"🔍 Filtering clauses by tag ID {tag_id}")
        
        # Verify the tag exists
        tag = db.query(Tag).filter(Tag.id == tag_id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        
        # Get clauses that have this tag
        clauses = db.query(ClauseLibrary).join(ClauseTag).filter(
            ClauseLibrary.saved_by == user_email,
            ClauseTag.tag_id == tag_id
        ).order_by(ClauseLibrary.created_at.desc()).all()
        
        clause_list = []
        
        for clause in clauses:
            # Get all tags for this clause
            clause_tag_objs = db.query(ClauseTag, Tag).join(
                Tag, ClauseTag.tag_id == Tag.id
            ).filter(
                ClauseTag.clause_id == clause.id
            ).all()
            
            tags = [
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category
                }
                for _, t in clause_tag_objs
            ]
            
            clause_list.append({
                "id": clause.id,
                "clause_title": clause.clause_title,
                "section_number": clause.section_number,
                "content_preview": (clause.clause_content[:200] + '...') if len(clause.clause_content) > 200 else clause.clause_content,
                "tags": tags,
                "saved_by": clause.saved_by,
                "created_at": clause.created_at.isoformat() if clause.created_at else None
            })
        
        return {
            "tag": {
                "id": tag.id,
                "name": tag.name,
                "category": tag.category
            },
            "clauses": clause_list,
            "count": len(clause_list),
            "user_email": user_email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error filtering clauses by tag: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clauses/library/filter/by-tag-name")
async def filter_clauses_by_tag_name(
    tag_name: str = Query(..., description="Tag name to filter by"),
    user_email: str = Query(..., description="Current user's email"),
    db: Session = Depends(get_db)
):
    """
    Filter saved clauses by a specific tag name
    """
    try:
        print(f"🔍 Filtering clauses by tag name: '{tag_name}'")
        
        # Find the tag by name
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            return {
                "tag_name": tag_name,
                "clauses": [],
                "count": 0,
                "message": "No clauses found with this tag"
            }
        
        # Get clauses that have this tag
        clauses = db.query(ClauseLibrary).join(ClauseTag).filter(
            ClauseLibrary.saved_by == user_email,
            ClauseTag.tag_id == tag.id
        ).order_by(ClauseLibrary.created_at.desc()).all()
        
        clause_list = []
        
        for clause in clauses:
            # Get all tags for this clause
            clause_tag_objs = db.query(ClauseTag, Tag).join(
                Tag, ClauseTag.tag_id == Tag.id
            ).filter(
                ClauseTag.clause_id == clause.id
            ).all()
            
            tags = [
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category
                }
                for _, t in clause_tag_objs
            ]
            
            clause_list.append({
                "id": clause.id,
                "clause_title": clause.clause_title,
                "section_number": clause.section_number,
                "content_preview": (clause.clause_content[:200] + '...') if len(clause.clause_content) > 200 else clause.clause_content,
                "tags": tags,
                "saved_by": clause.saved_by,
                "created_at": clause.created_at.isoformat() if clause.created_at else None
            })
        
        return {
            "tag": {
                "id": tag.id,
                "name": tag.name,
                "category": tag.category
            },
            "clauses": clause_list,
            "count": len(clause_list),
            "user_email": user_email
        }
        
    except Exception as e:
        print(f"❌ Error filtering clauses by tag name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clauses/library/with-tags")
async def get_clauses_with_tags(
    user_email: str = Query(..., description="Current user's email"),
    db: Session = Depends(get_db)
):
    """
    Get all saved clauses with their tags
    """
    try:
        print(f"🔍 Getting all clauses with tags for user: {user_email}")
        
        # Get all clauses for the user
        clauses = db.query(ClauseLibrary).filter(
            ClauseLibrary.saved_by == user_email
        ).order_by(ClauseLibrary.created_at.desc()).all()
        
        clause_list = []
        
        for clause in clauses:
            # Get all tags for this clause
            clause_tag_objs = db.query(ClauseTag, Tag).join(
                Tag, ClauseTag.tag_id == Tag.id
            ).filter(
                ClauseTag.clause_id == clause.id
            ).all()
            
            tags = [
                {
                    "id": t.id,
                    "name": t.name,
                    "category": t.category
                }
                for _, t in clause_tag_objs
            ]
            
            clause_list.append({
                "id": clause.id,
                "clause_title": clause.clause_title,
                "section_number": clause.section_number,
                "content_preview": (clause.clause_content[:200] + '...') if len(clause.clause_content) > 200 else clause.clause_content,
                "tags": tags,
                "tag_count": len(tags),
                "saved_by": clause.saved_by,
                "created_at": clause.created_at.isoformat() if clause.created_at else None
            })
        
        return {
            "clauses": clause_list,
            "count": len(clause_list),
            "user_email": user_email
        }
        
    except Exception as e:
        print(f"❌ Error getting clauses with tags: {e}")
        raise HTTPException(status_code=500, detail=str(e))

