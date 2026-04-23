from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

import config

from database import get_db
from core.google_client import drive_client

# Initialize router
router = APIRouter()

# Models
from models.metadata import (
    Document,
    DocumentTag,
    Tag,
    PracticeArea,
    SubPracticeArea,
    ContentType
)
from models.clauses import DocumentClause

from pydantic import BaseModel

class TagUpdateRequest(BaseModel):
    tag: str


# ==================== SERVICES ====================
from services.drive_ingestion import DriveIngestionService

# ==================== HELPERS ====================
def get_current_user_email():
    """
    Get the currently logged-in user's email from Google Drive
    """
    if not drive_client or not drive_client.creds:
        return None

    try:
        about = drive_client.service.about().get(fields='user').execute()
        return about['user']['emailAddress']
    except Exception as e:
        print(f"⚠️ Error getting current user: {e}")
        return None

def _get_document_by_any_id(db: Session, document_id: str):
    from models.metadata import Document
    from core.google_client import drive_client
    from services.drive_ingestion import DriveIngestionService

    # 1️⃣ Try DB id
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        return doc

    # 2️⃣ Try drive_file_id
    doc = db.query(Document).filter(Document.drive_file_id == document_id).first()
    if doc:
        return doc

    # 🔥 3️⃣ FORCE SYNC
    try:
        print(f"🔄 Syncing missing document: {document_id}")
        ingestion = DriveIngestionService(drive_client, db)
        ingestion.sync_all_files()

        # Try again
        doc = db.query(Document).filter(Document.drive_file_id == document_id).first()
        if doc:
            print("✅ Found after sync")
            return doc

        # 🔥🔥🔥 NEW FIX: CREATE DOCUMENT MANUALLY
        print("⚠️ Not found even after sync, creating manually...")

        file_data = drive_client.get_file(document_id)

        metadata = ingestion._extract_metadata(file_data, account_email=None)

        new_doc = Document(**metadata)
        db.add(new_doc)
        db.commit()

        print("✅ Document manually created in DB")

        return new_doc

    except Exception as e:
        print(f"❌ FINAL FAIL: {e}")

    return None


def _load_tags_from_doc(doc, db: Session):
    """
    Load tag names for a document
    """
    doc_tags = db.query(DocumentTag, Tag).join(
        Tag, DocumentTag.tag_id == Tag.id
    ).filter(
        DocumentTag.document_id == doc.id
    ).all()

    return [tag.name for _, tag in doc_tags]


def _save_tags_to_doc(doc, tag_names, db: Session):
    """
    Replace all tags on a document safely
    """
    try:
        db.query(DocumentTag).filter(
            DocumentTag.document_id == doc.id
        ).delete()

        for name in tag_names:
            clean = name.strip()
            if not clean:
                continue

            tag = db.query(Tag).filter(Tag.name == clean).first()
            if not tag:
                tag = Tag(name=clean, category="custom")
                db.add(tag)
                db.flush()

            db.add(DocumentTag(
                document_id=doc.id,
                tag_id=tag.id
            ))

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Tag save error: {e}")
        raise


# ==================== ROUTES ====================

@router.get("/documents")
async def get_all_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    try:
        current_user = get_current_user_email()

        if not current_user:
            return {
                "documents": [],
                "total": 0,
                "skip": skip,
                "limit": limit,
                "current_user": None,
                "message": "Not authenticated"
            }

        print(f"📧 Fetching documents for user: {current_user}")

        # 🔥🔥🔥 ADD THIS BLOCK (MAIN FIX)
        try:
            print("🔄 Running background sync before fetching documents...")
            ingestion = DriveIngestionService(drive_client, db)
            ingestion.sync_all_files()
        except Exception as e:
            print(f"⚠️ Sync failed but continuing: {e}")
        # 🔥🔥🔥 END FIX

        documents = db.query(Document).filter(
            Document.account_email == current_user
        ).offset(skip).limit(limit).all()

        total = db.query(Document).filter(
            Document.account_email == current_user
        ).count()

        return {
            "documents": [
                {
                    "id": doc.id,
                    "title": doc.title,
                    "mime_type": doc.mime_type,
                    "size_bytes": doc.size_bytes,
                    "owner_name": doc.owner_name,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None,
                    "modified_at": doc.modified_at.isoformat() if doc.modified_at else None,
                    "file_url": doc.file_url,
                    "status": doc.status,
                    "account_email": doc.account_email
                }
                for doc in documents
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
            "current_user": current_user
        }

    except Exception as e:
        import traceback
        print(f"❌ Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{doc_id}/metadata")
async def get_document_metadata(doc_id: str, db: Session = Depends(get_db)):
    """Get document metadata for Template Library editing"""
    doc = _get_document_by_any_id(db, doc_id)
    if not doc:
        return {"tags": []}   # ✅ NO ERROR
    
    # Get sub-practice details
    sub_practice = db.query(SubPracticeArea).filter(SubPracticeArea.sub_practice_id == doc.sub_practice_id).first()
    practice_area = db.query(PracticeArea).filter(PracticeArea.practice_area_id == sub_practice.practice_area_id).first() if sub_practice else None
    
    return {
        "id": doc.id,
        "title": doc.title,
        "content_type": doc.content_type.value if doc.content_type else None,
        "sub_practice_id": doc.sub_practice_id,
        "sub_practice_name": sub_practice.sub_practice_name if sub_practice else None,
        "practice_area_name": practice_area.practice_area_name if practice_area else None,
        "workflow_status": doc.workflow_status,
        "bucket": doc.bucket,
        "variant": doc.variant,
        "certified_by": doc.certified_by,
        "certified_at": doc.certified_at.isoformat() if doc.certified_at else None,
        "version_number": doc.version_number
    }

@router.put("/documents/{doc_id}/metadata")
async def update_document_metadata(doc_id: str, metadata: dict, db: Session = Depends(get_db)):
    """Update document metadata for Template Library"""
    doc = _get_document_by_any_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Update allowed fields only
    update_fields = {
        'content_type': metadata.get('content_type'),
        'sub_practice_id': metadata.get('sub_practice_id'),
        'workflow_status': metadata.get('workflow_status'),
        'bucket': metadata.get('bucket'),
        'variant': metadata.get('variant'),
        'certified_by': metadata.get('certified_by'),
        'certified_at': metadata.get('certified_at'),
        'version_number': metadata.get('version_number')
    }
    
    for field, value in update_fields.items():
        if value is not None:
            setattr(doc, field, value)
    
    db.commit()
    db.refresh(doc)
    return {"status": "success", "message": "Metadata updated successfully"}

@router.get("/documents/template-stats")
async def get_template_stats(db: Session = Depends(get_db)):
    """Get statistics about templates vs other documents"""
    try:
        # Get current user
        current_user = get_current_user_email()
        if not current_user:
            return {"error": "Not authenticated"}
        
        # Count documents by content_type for current user
        templates = db.query(Document).filter(
            Document.account_email == current_user,
            Document.content_type == ContentType.TEMPLATE
        ).count()
        
        others = db.query(Document).filter(
            Document.account_email == current_user,
            Document.content_type == ContentType.OTHER
        ).count()
        
        total = db.query(Document).filter(
            Document.account_email == current_user
        ).count()
        
        return {
            "templates": templates,
            "other_documents": others,
            "total_documents": total,
            "template_percentage": round((templates / total * 100), 2) if total > 0 else 0
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DOCUMENT - TAG ROUTES ====================

@router.get("/documents/{document_id}/tags")
async def get_document_tags(document_id: str, db: Session = Depends(get_db)):
    """Get tags for document by any ID type (Drive ID or internal ID)"""
    try:
        doc = _get_document_by_any_id(db, document_id)  # Uses both lookup methods
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        tags = _load_tags_from_doc(doc, db)
        return {"tags": tags}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/documents/{document_id}/tags/add")
async def add_document_tag(document_id: str, payload: TagUpdateRequest, db: Session = Depends(get_db)):
    print("\n================ TAG ADD DEBUG START ================")

    try:
        print("➡️ URL document_id:", document_id)

        tag_name = (payload.tag or "").strip()
        print("➡️ Payload tag:", tag_name)

        if not tag_name:
            raise HTTPException(status_code=400, detail="Tag cannot be empty")

        # STEP 1: Find document
        doc = db.query(Document).filter(
            (Document.drive_file_id == document_id) | (Document.id == document_id)
        ).first()

        print("➡️ Document found:", bool(doc))
        if doc:
            print("   doc.id:", doc.id)
            print("   doc.drive_file_id:", doc.drive_file_id)

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # STEP 2: Get or create tag
        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        print("➡️ Tag exists:", bool(tag))

        if not tag:
            tag = Tag(name=tag_name, category="user")
            db.add(tag)
            db.flush()
            print("✅ Tag created with id:", tag.id)
        else:
            print("➡️ Tag id:", tag.id)

        # STEP 3: Check existing relation
        existing = db.execute(
            text("""
                SELECT id FROM document_tags
                WHERE document_id = :doc_id AND tag_id = :tag_id
            """),
            {"doc_id": doc.id, "tag_id": tag.id}
        ).fetchone()

        print("➡️ Existing document_tag row:", existing)

        if not existing:
            print("➡️ Attempting INSERT into document_tags")

            result = db.execute(
                text("""
                    INSERT INTO document_tags
                    (document_id, tag_id, source, created_by, created_at)
                    VALUES (:doc_id, :tag_id, 'user', 'web_ui', NOW())
                """),
                {"doc_id": doc.id, "tag_id": tag.id}
            )

            print("➡️ INSERT executed")
            print("➡️ rowcount:", result.rowcount)

        print("➡️ Committing transaction")
        db.commit()

        # STEP 5: Fetch ALL tags for this document
        all_tags = db.query(Tag.name).join(
            DocumentTag, Tag.id == DocumentTag.tag_id
        ).filter(
            DocumentTag.document_id == doc.id
        ).all()

        tags_list = [t[0] for t in all_tags]


        # STEP 4: VERIFY USING SAME CONNECTION
        verify = db.execute(
            text("""
                SELECT id, document_id, tag_id
                FROM document_tags
                WHERE document_id = :doc_id AND tag_id = :tag_id
            """),
            {"doc_id": doc.id, "tag_id": tag.id}
        ).fetchall()

        print("🔥 VERIFICATION ROWS AFTER COMMIT:", verify)

        # EXTRA: show DB name + connection id
        db_name = db.execute(text("SELECT DATABASE()")).scalar()
        conn_id = db.execute(text("SELECT CONNECTION_ID()")).scalar()
        print("🔥 DATABASE:", db_name)
        print("🔥 CONNECTION_ID:", conn_id)

        print("================ TAG ADD DEBUG END =================\n")

        return {
            "success": True,
            "document_id": document_id,
            "tags": tags_list,
            "message": f"Tag '{tag_name}' added (debug mode)"
        }

    except Exception as e:
        print("❌ EXCEPTION:", e)
        db.rollback()
        raise


@router.post("/documents/{document_id}/tags/remove")
async def remove_document_tag(document_id: str, payload: TagUpdateRequest, db: Session = Depends(get_db)):
    try:
        tag_name = (payload.tag or "").strip()
        if not tag_name:
            raise HTTPException(status_code=400, detail="Tag cannot be empty")

        doc = db.query(Document).filter(
            (Document.drive_file_id == document_id) | (Document.id == document_id)
        ).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        effective_document_id = document_id  # 🔥

        tag = db.query(Tag).filter(Tag.name == tag_name).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")

        doc_tag = db.query(DocumentTag).filter(
            DocumentTag.document_id == effective_document_id,
            DocumentTag.tag_id == tag.id
        ).first()

        if doc_tag:
            db.delete(doc_tag)
            db.commit()

        all_tags_from_db = db.query(Tag.name).join(
            DocumentTag, Tag.id == DocumentTag.tag_id
        ).filter(
            DocumentTag.document_id == effective_document_id
        ).all()

        tags_list = [t[0] for t in all_tags_from_db if t and t[0]]

        return {
            "success": True,
            "document_id": effective_document_id,
            "tags": tags_list
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ==================== TEMPLATE SPECIFIC DOCUMENT ROUTES ====================

@router.get("/templates")
async def list_templates(
    practice_area: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get ALL TEMPLATE files (content_type = 'template') from connected Drive
    Show ALL template files (even without tags)
    Only tags from template files appear in practice areas
    """
    try:
        current_user = get_current_user_email()
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        templates = []
        all_tags_set = set()  # Will collect tags ONLY from template files
        
        print(f"📂 Loading ALL TEMPLATE files for: {current_user}")
        
        # 1. Get all files from Drive
        drive_files = []
        try:
            if 'drive_client' in globals() and drive_client and drive_client.creds:
                results = drive_client.list_files(page_size=100)
                drive_files = results.get('files', [])
                print(f"✅ Retrieved {len(drive_files)} files from Drive")
        except Exception as e:
            print(f"⚠️ Drive error: {e}")
            return {"templates": [], "practice_areas": [], "total": 0}
        
        # 2. Process each Drive file
        for file in drive_files:
            try:
                # ✅ SKIP FOLDERS
                mime_type = file.get('mimeType', '')
                if mime_type == 'application/vnd.google-apps.folder':
                    print(f"⏭️ Skipping folder: {file['name']}")
                    continue
                
                file_id = file.get('id')
                
                # ✅ CHECK IF FILE EXISTS IN DB AND IS A TEMPLATE
                doc = db.query(Document).filter(
                    Document.drive_file_id == file_id,
                    Document.account_email == current_user,
                    Document.content_type == ContentType.TEMPLATE  # ← ONLY TEMPLATES
                ).first()
                
                # Skip if file not in DB or not a template
                if not doc:
                    print(f"⏭️ Skipping non-template or not in DB: {file['name']}")
                    continue
                
                # ✅ GET TAGS FOR THIS TEMPLATE FILE (if any)
                tags_query = db.query(Tag.name).join(DocumentTag).filter(
                    DocumentTag.document_id == doc.id
                ).all()
                
                # ✅ Extract and clean tag names
                tag_names = []
                for tag_tuple in tags_query:
                    if tag_tuple and len(tag_tuple) > 0:
                        tag_name = tag_tuple[0]  # Access first element of tuple
                        if tag_name and isinstance(tag_name, str):
                            # Clean the tag - strip whitespace and remove quotes
                            clean_tag = tag_name.strip()
                            # Remove surrounding quotes if present
                            if clean_tag.startswith("'") and clean_tag.endswith("'"):
                                clean_tag = clean_tag[1:-1]
                            elif clean_tag.startswith('"') and clean_tag.endswith('"'):
                                clean_tag = clean_tag[1:-1]
                            
                            if clean_tag:  # Only add non-empty tags
                                tag_names.append(clean_tag)
                
                # ✅ ADD CLEAN TAGS TO PRACTICE AREA SET (only from template files)
                for tag in tag_names:
                    all_tags_set.add(tag)
                
                # ✅ NOW tag_names is guaranteed to be list of clean strings
                file_name_lower = file.get('name', '').lower()
                tags_lower = [t.lower() for t in tag_names]
                
                # Filter by search
                if search and search.strip():
                    search_lower = search.lower()
                    if search_lower not in file_name_lower and not any(search_lower in t for t in tags_lower):
                        continue
                
                # Filter by practice area
                if practice_area and practice_area.strip():
                    practice_area_lower = practice_area.lower()
                    if not any(practice_area_lower in t for t in tags_lower):
                        continue
                
                # ✅ Get owner info
                owner_name = "Unknown"
                owners_list = file.get("owners", [])
                if owners_list and isinstance(owners_list, list) and len(owners_list) > 0:
                    first_owner = owners_list[0] if len(owners_list) > 0 else {}
                    if isinstance(first_owner, dict):
                        owner_name = first_owner.get("displayName", "Unknown")
                
                # ✅ ADD ALL TEMPLATE FILES (even without tags)
                template_data = {
                    "id": file_id,
                    "name": file.get('name', 'Untitled'),
                    "title": file.get('name', 'Untitled'),
                    "owner": owner_name,
                    "modifiedTime": file.get("modifiedTime"),
                    "size": int(file.get("size", 0)),
                    "mimeType": mime_type,
                    "aiTags": tag_names,  # Empty list if no tags (already cleaned)
                    "tagCount": len(tag_names),
                    "fileUrl": file.get("webViewLink"),
                    "type": "document",
                    "content_type": "template"  # Always template for this endpoint
                }
                
                templates.append(template_data)
                
                if tag_names:
                    print(f"✅ Template with {len(tag_names)} tags: {file['name']}")
                else:
                    print(f"📋 Template (no tags): {file['name']}")
                
            except Exception as file_error:
                print(f"⚠️ Error processing file {file.get('name', 'Unknown')}: {file_error}")
                import traceback
                traceback.print_exc()
                continue
        
        # Convert tags set to sorted list (practice areas)
        practice_areas = sorted(list(all_tags_set))
        
        print(f"✅ Found {len(templates)} template files | Practice Areas: {len(practice_areas)}")
        
        return {
            "templates": templates,
            "practice_areas": practice_areas,
            "total": len(templates),
            "current_user": current_user,
            "message": f"Showing all {len(templates)} template files"
        }
        
    except Exception as e:
        print(f"❌ Templates error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@router.post("/templates/cleanup-prod")
async def cleanup_templates(db: Session = Depends(get_db)):
    """Remove deleted/orphan files from templates"""
    current_user = get_current_user_email()
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Delete orphans: no drive file + zero size + no URL
    orphans = db.query(Document).filter(
        Document.account_email == current_user,
        Document.drive_file_id.is_(None),
        Document.size_bytes == 0,
        Document.file_url.is_(None)
    ).delete(synchronize_session=False)
    db.commit()
    
    return {
        "cleaned": orphans,
        "message": f"Removed {orphans} orphan template records"
    }

# ==================== DRIVE - DB DOCUMENT SYNC ROUTES ====================

@router.post("/sync/drive-full")
async def sync_drive_full(db: Session = Depends(get_db)):
    """
    Manually trigger full Google Drive → DB sync.
    """
    if not drive_client or not drive_client.creds:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        ingestion = DriveIngestionService(drive_client, db)
        stats = ingestion.sync_all_files()
        return {"message": "Sync completed", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sync/status")
async def get_sync_status(db: Session = Depends(get_db)):
    """
    Get sync status and statistics
    """
    try:
        ingestion_service = DriveIngestionService(drive_client, db)
        stats = ingestion_service.get_sync_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#==================== FILE PREVIEW ROUTES ====================
@router.get("/files/{file_id}/preview")
async def get_file_preview(file_id: str, db: Session = Depends(get_db)):
    """Get file preview information"""
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # Get document from database
        document = db.query(Document).filter(Document.id == file_id).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="File not found")
        
        # Get tags for this document
        from models.metadata import DocumentTag, Tag
        doc_tags = db.query(DocumentTag, Tag).join(
            Tag, DocumentTag.tag_id == Tag.id
        ).filter(
            DocumentTag.document_id == file_id
        ).all()
        
        tags = [
            {
                'id': tag.id,
                'name': tag.name,
                'category': tag.category
            }
            for doc_tag, tag in doc_tags
        ]
        
        # Determine preview type based on mime type
        mime_type = document.mime_type or ''
        
        if 'pdf' in mime_type:
            preview_type = 'pdf'
        elif 'image' in mime_type:
            preview_type = 'image'
        elif 'google-apps.document' in mime_type or 'google-apps.spreadsheet' in mime_type or 'google-apps.presentation' in mime_type:
            preview_type = 'google_embed'
        elif 'word' in mime_type or 'document' in mime_type:
            preview_type = 'document'
        else:
            preview_type = 'download_only'
        
        return {
            'id': document.id,
            'title': document.title,
            'mime_type': document.mime_type,
            'size_bytes': document.size_bytes,
            'size_mb': round(document.size_bytes / (1024 * 1024), 2) if document.size_bytes else 0,
            'owner_name': document.owner_name,
            'owner_email': document.owner_email,
            'created_at': document.created_at.isoformat() if document.created_at else None,
            'modified_at': document.modified_at.isoformat() if document.modified_at else None,
            'file_url': document.file_url,
            'thumbnail_link': document.thumbnail_link,
            'preview_type': preview_type,
            'tags': tags
        }
        
    except Exception as e:
        print(f"❌ Preview error: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
   

# ==================== AND TAG SEARCH API ====================

@router.get("/documents/search/by-tags")
def search_documents_by_tags(
    tags: str = Query(..., description="Comma separated tag names"),
    db: Session = Depends(get_db)
):
    """
    AND search → document must contain ALL tags
    Example:
    /documents/search/by-tags?tags=nda,employment
    """

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    if not tag_list:
        return {"documents": []}

    print("🔍 AND TAG SEARCH:", tag_list)

    # STEP 1: Get tag IDs
    tag_rows = db.query(Tag).filter(Tag.name.in_(tag_list)).all()

    if len(tag_rows) != len(tag_list):
        return {"documents": []}  # some tags not exist

    tag_ids = [t.id for t in tag_rows]

    # STEP 2: AND LOGIC
    results = (
        db.query(Document)
        .join(DocumentTag, Document.id == DocumentTag.document_id)
        .filter(DocumentTag.tag_id.in_(tag_ids))
        .group_by(Document.id)
        .having(text("COUNT(DISTINCT document_tags.tag_id) = :count"))
        .params(count=len(tag_ids))
        .all()
    )

    print(f"✅ Found {len(results)} documents")

    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "file_url": doc.file_url
            }
            for doc in results
        ]
    }


# ==================== TAG SUGGESTION API ====================

@router.get("/tags/suggest")
def suggest_tags(
    q: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Auto-suggest tags (LIKE search)
    """

    results = db.query(Tag).filter(
        Tag.name.ilike(f"{q}%")
    ).limit(10).all()

    return {
        "tags": [t.name for t in results]
    }