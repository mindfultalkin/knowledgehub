"""
Document management controllers
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import models and services
from database import get_db
from app.models.document import Document
from app.models.tag import Tag, DocumentTag  # Make sure these are imported
from app.models.practice_area import PracticeArea, SubPracticeArea
from app.services.google_drive_service import GoogleDriveClient
from app.services.document_processor_service import DocumentProcessor
from app.controllers.auth_controller import get_current_user_email
router = APIRouter()

# Initialize Google Drive client
try:
    drive_client = GoogleDriveClient()
    doc_processor = DocumentProcessor(drive_client)
except Exception as e:
    print(f"⚠️ Warning: Could not initialize drive client: {e}")
    drive_client = None
    doc_processor = None

# ==================== HELPER FUNCTIONS ====================

def _get_document_by_any_id(db: Session, doc_id: str):
    # Try primary key
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        return doc
    # Try drive_file_id (when frontend passes Drive ID)
    return db.query(Document).filter(Document.drive_file_id == doc_id).first()

def get_content_preview(content: str, query: str, preview_length: int = 200) -> str:
    """Get content preview for simple search"""
    if not content or not query:
        return content[:preview_length] + '...' if len(content) > preview_length else content
    
    content_lower = content.lower()
    query_words = [word.lower() for word in query.split() if len(word) > 2]
    
    for word in query_words:
        position = content_lower.find(word)
        if position != -1:
            start = max(0, position - 50)
            end = min(len(content), position + 150)
            return f"...{content[start:end]}..."
    
    return content[:preview_length] + '...' if len(content) > preview_length else content

def _load_tags_from_doc(doc, db: Session):
    """
    Load tag NAMES for a document from DocumentTag/Tag tables.
    """
    from app.models.tag import Tag, DocumentTag
    
    # Query tags for this document
    tags = db.query(Tag).join(
        DocumentTag, Tag.id == DocumentTag.tag_id
    ).filter(
        DocumentTag.document_id == doc.id
    ).all()
    
    return [tag.name for tag in tags if tag and tag.name]

# ==================== DOCUMENT ROUTES ====================

@router.get("/documents")
async def get_all_documents(
    skip: int = 0,
    limit: int = 200,  # Increased from 50 to 200
    db: Session = Depends(get_db)
):
    """
    Get all documents from database with pagination - FILTERED BY CURRENT USER
    """
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
        
        # Get documents from database
        documents = db.query(Document).filter(
            Document.account_email == current_user
        ).offset(skip).limit(limit).all()
        
        total = db.query(Document).filter(
            Document.account_email == current_user
        ).count()
        
        print(f"📊 Found {len(documents)}/{total} documents for {current_user}")
        
        # Format response with tags
        formatted_docs = []
        for doc in documents:
            # Get tags for each document
            tags = _load_tags_from_doc(doc, db)
            
            formatted_docs.append({
                "id": doc.id,
                "title": doc.title,
                "mime_type": doc.mime_type,
                "size_bytes": doc.size_bytes,
                "owner_name": doc.owner_name,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "modified_at": doc.modified_at.isoformat() if doc.modified_at else None,
                "file_url": doc.file_url,
                "status": doc.status,
                "account_email": doc.account_email,
                "tags": tags,  # Add tags to response
                "tag_count": len(tags)
            })
        
        return {
            "documents": formatted_docs,
            "total": total,
            "skip": skip,
            "limit": limit,
            "current_user": current_user
        }
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drive/all-files")
async def get_all_drive_files(
    db: Session = Depends(get_db)
):
    """
    Get ALL files directly from Google Drive (not limited by database)
    """
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        current_user = get_current_user_email()
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")

        print(f"📂 Getting ALL files from Drive for: {current_user}")
        
        # Get all files from Drive (no pagination limit)
        all_files = []
        page_token = None
        
        while True:
            results = drive_client.list_files(page_size=100, page_token=page_token)
            files = results.get("files", [])
            all_files.extend(files)
            
            page_token = results.get("nextPageToken")
            if not page_token:
                break
        
        print(f"✅ Retrieved {len(all_files)} total files from Drive")
        
        # Process files with tags from database
        formatted_files = []
        for file in all_files:
            try:
                # Skip folders
                mime_type = file.get('mimeType', '')
                if mime_type == 'application/vnd.google-apps.folder':
                    continue
                
                file_id = file.get('id')
                
                # Find document in database
                doc = db.query(Document).filter(
                    Document.drive_file_id == file_id,
                    Document.account_email == current_user
                ).first()
                
                # Get tags if document exists
                tags = []
                if doc:
                    tags = _load_tags_from_doc(doc, db)
                
                # Get owner name
                owner_name = "Unknown"
                owners_list = file.get("owners", [])
                if owners_list and len(owners_list) > 0:
                    first_owner = owners_list[0]
                    owner_name = first_owner.get("displayName", "Unknown")
                
                formatted_files.append({
                    "id": file_id,
                    "name": file.get('name', 'Untitled'),
                    "mimeType": mime_type,
                    "size": int(file.get("size", 0)),
                    "modifiedTime": file.get("modifiedTime"),
                    "createdTime": file.get("createdTime"),
                    "owner": owner_name,
                    "thumbnailLink": file.get("thumbnailLink"),
                    "webViewLink": file.get("webViewLink"),
                    "iconLink": file.get("iconLink"),
                    "aiTags": tags,
                    "tagCount": len(tags),
                    "type": "file",
                    "in_database": doc is not None
                })
                
            except Exception as file_error:
                print(f"⚠️ Error processing file: {file_error}")
                continue
        
        return {
            "files": formatted_files,
            "totalCount": len(formatted_files),
            "currentUser": current_user,
            "source": "google_drive_all"
        }
        
    except Exception as e:
        print(f"❌ Error getting all files: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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

@router.get("/drive/files")
async def get_files(
    page_size: int = 50, 
    page_token: Optional[str] = None, 
    query: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List files from Google Drive + ADD TAGS from document_tags table
    Fixed to handle both Drive file ID and internal Document ID lookups
    """
    if not drive_client:
        raise HTTPException(status_code=500, detail="Services not initialized")
    
    try:
        if not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # Get current user's email
        try:
            about = drive_client.service.about().get(fields='user').execute()
            current_user = about['user']['emailAddress']
            print(f"📧 Loading files for user: {current_user}")
        except Exception as e:
            print(f"⚠️ Could not get current user: {e}")
            current_user = None

        # Get files from LIVE Google Drive
        results = drive_client.list_files(page_size, page_token, query)

        files = []
        for file in results.get("files", []):
            # ✅ FIXED: Use _get_document_by_any_id to lookup by BOTH Drive ID and internal ID
            doc = _get_document_by_any_id(db, file["id"])
            
            # ✅ FIXED: Get tags with fallback for direct drive_file_id lookup
            ai_tags = []
            tag_count = 0
            if doc:
                # Primary: Use Document.id from lookup
                doc_tags = db.query(DocumentTag).filter(
                    DocumentTag.document_id == doc.id
                ).join(Tag).all()
                ai_tags = [dt.tag.name for dt in doc_tags]
                tag_count = len(ai_tags)
                print(f"🏷️ Found {tag_count} tags for {file['name']} via doc.id={doc.id}")
            else:
                # Fallback: Direct query by drive_file_id if no Document record
                doc_tags = db.query(DocumentTag).join(Document).join(Tag).filter(
                    Document.drive_file_id == file["id"]
                ).all()
                ai_tags = [dt.tag.name for dt in doc_tags]
                tag_count = len(ai_tags)
                print(f"🏷️ Found {tag_count} tags for {file['name']} via direct drive_file_id")

            file_data = {
                "id": file["id"],
                "name": file["name"],
                "mimeType": file.get("mimeType", ""),
                "size": file.get("size", "0"),
                "modifiedTime": file.get("modifiedTime", ""),
                "createdTime": file.get("createdTime", ""),
                "owner": file.get("owners", [{}])[0].get("displayName", "Unknown") if file.get("owners") else "Unknown",
                "thumbnailLink": file.get("thumbnailLink"),
                "webViewLink": file.get("webViewLink"),
                "iconLink": file.get("iconLink"),
                "aiTags": ai_tags,        # ✅ Always populated from DB
                "tagCount": tag_count,    # ✅ Accurate count
                "type": "file",
                "currentUser": current_user
            }
            files.append(file_data)

        return {
            "files": files, 
            "nextPageToken": results.get("nextPageToken"), 
            "totalCount": len(files),
            "currentUser": current_user
        }

    except Exception as e:
        print(f"❌ Error getting files: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drive/files/{file_id}")
async def get_file(file_id: str):
    """Get specific file details"""
    if not drive_client or not tagger:
        raise HTTPException(status_code=500, detail="Services not initialized")
    
    try:
        if not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        file = drive_client.get_file(file_id)
        tags = tagger.generate_tags(file["name"], file.get("mimeType"), file.get("description"))
        return {**file, "aiTags": tags, "type": tagger.detect_file_type(file.get("mimeType", ""))}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/drive/connection-status")
async def connection_status():
    """Get Google Drive connection status"""
    if not drive_client:
        return {"connected": False, "error": "Drive client not initialized"}
    
    try:
        if not drive_client.creds:
            return {"connected": False, "message": "Not authenticated"}

        about = drive_client.get_about()
        storage = about.get("storageQuota", {})

        return {
            "connected": True,
            "user": {
                "email": about["user"]["emailAddress"],
                "displayName": about["user"]["displayName"],
            },
            "storage": {
                "limit": storage.get("limit", "0"),
                "usage": storage.get("usage", "0"),
                "usageInDrive": storage.get("usageInDrive", "0"),
            },
        }

    except Exception as e:
        return {"connected": False, "error": str(e)}

@router.get("/drive/files-live")
async def get_files_live(
    page_size: int = 50, 
    page_token: Optional[str] = None, 
    query: Optional[str] = None
):
    """
    Get files DIRECTLY from Google Drive API (before sync to database)
    This is used when database is empty to show files in real-time
    """
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    
    if not tagger:
        raise HTTPException(status_code=500, detail="Tagger not initialized")
    
    try:
        if not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")

        # Get files from LIVE Google Drive API
        results = drive_client.list_files(
            page_size=page_size, 
            page_token=page_token,
            query=query
        )

        files = []
        for file in results.get("files", []):
            try:
                tags = tagger.generate_tags(file.get('name', ''), file.get("mimeType", ""), file.get("description"))
                file_data = {
                    "id": file["id"],
                    "name": file["name"],
                    "mimeType": file.get("mimeType", ""),
                    "size": file.get("size", "0"),
                    "modifiedTime": file.get("modifiedTime", ""),
                    "createdTime": file.get("createdTime", ""),
                    "owner": file.get("owners", [{}])[0].get("displayName", "Unknown") if file.get("owners") else "Unknown",
                    "thumbnailLink": file.get("thumbnailLink"),
                    "webViewLink": file.get("webViewLink"),
                    "iconLink": file.get("iconLink"),
                    "aiTags": tags,
                    "type": tagger.detect_file_type(file.get("mimeType", "")),
                    "source": "google_drive_live"  # Show this is from live API
                }
                files.append(file_data)
            except Exception as e:
                print(f"⚠️ Error processing file: {e}")
                continue

        return {
            "files": files, 
            "nextPageToken": results.get("nextPageToken"),
            "totalCount": len(files),
            "source": "google_drive_live"
        }

    except Exception as e:
        print(f"❌ Error getting live files: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

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

@router.get("/documents/{doc_id}/metadata")
async def get_document_metadata(doc_id: str, db: Session = Depends(get_db)):
    """Get document metadata for Template Library editing"""
    doc = get_document_by_any_id(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
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
    doc = get_document_by_any_id(db, doc_id)
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

@router.get("/search/grouped")
async def grouped_search(query: str, content_type: str = None, db: Session = Depends(get_db)):
    """Grouped search: Templates, Clauses, Practice Notes, Knowledge Materials"""
    current_user = get_current_user_email()
    
    results = {
        "templates": [],
        "clause_sets": [],
        "practice_notes": [],
        "knowledge_materials": [],
        "total": 0
    }
    
    # Search documents by content type
    content_types = []
    if content_type == "templates":
        content_types = ["template"]
    elif content_type == "clauses":
        content_types = ["clause_set"]
    elif content_type == "notes":
        content_types = ["practice_note"]
    elif content_type == "materials":
        content_types = ["knowledge_material"]
    else:
        content_types = ["template", "clause_set", "practice_note", "knowledge_material"]
    
    documents = db.query(Document).filter(
        Document.account_email == current_user,
        Document.title.ilike(f"%{query}%"),
        Document.content_type.in_(content_types)
    ).limit(10).all()
    
    # Group results
    for doc in documents:
        if doc.content_type == "template":
            results["templates"].append({
                "id": doc.id,
                "title": doc.title,
                "practice_area": doc.sub_practice_area.practice_area.practice_area_name if doc.sub_practice_area and doc.sub_practice_area.practice_area else "Uncategorized",
                "sub_practice": doc.sub_practice_area.sub_practice_name if doc.sub_practice_area else "Uncategorized",
                "variant": doc.variant,
                "workflow_status": doc.workflow_status,
                "file_url": doc.file_url
            })
        elif doc.content_type == "clause_set":
            results["clause_sets"].append({"id": doc.id, "title": doc.title, "file_url": doc.file_url})
        elif doc.content_type == "practice_note":
            results["practice_notes"].append({"id": doc.id, "title": doc.title, "file_url": doc.file_url})
        elif doc.content_type == "knowledge_material":
            results["knowledge_materials"].append({"id": doc.id, "title": doc.title, "file_url": doc.file_url})
    
    results["total"] = len(documents)
    return results

@router.get("/templates")
async def list_templates(
    practice_area: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get ALL files from connected Drive WITH TAGS (skip folders, skip files without tags)
    """
    try:
        current_user = get_current_user_email()
        if not current_user:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        templates = []
        all_tags_set = set()
        
        print(f"\n📂 ====== TEMPLATES DEBUG START ======")
        print(f"📂 Loading files from Drive for: {current_user}")
        
        # 1. Get all files from Drive
        drive_files = []
        try:
            if drive_client and drive_client.creds:
                results = drive_client.list_files(page_size=200)  # Get more files
                drive_files = results.get('files', [])
                print(f"✅ Retrieved {len(drive_files)} files from Drive")
            else:
                print("❌ Drive client not authenticated")
                return {"templates": [], "practice_areas": [], "total": 0}
        except Exception as e:
            print(f"⚠️ Drive error: {e}")
            return {"templates": [], "practice_areas": [], "total": 0}
        
        # 2. Process each Drive file
        for i, file in enumerate(drive_files[:20]):  # Process first 20 for debugging
            try:
                print(f"\n--- File {i+1}: {file.get('name', 'Unknown')} ---")
                
                # ✅ SKIP FOLDERS
                mime_type = file.get('mimeType', '')
                if mime_type == 'application/vnd.google-apps.folder':
                    print(f"⏭️ Skipping folder")
                    continue
                
                file_id = file.get('id')
                print(f"📄 File ID: {file_id}")
                
                # ✅ CHECK IF FILE EXISTS IN DB (by drive_file_id)
                doc = db.query(Document).filter(
                    Document.drive_file_id == file_id,
                    Document.account_email == current_user
                ).first()
                
                if not doc:
                    print(f"⚠️ File not found in database")
                    continue
                
                print(f"📄 Found in DB: {doc.title} (DB ID: {doc.id})")
                
                # ✅ GET TAGS FOR THIS FILE
                from app.models.tag import DocumentTag
                
                # Debug: Count total tags in database
                total_tags = db.query(Tag).count()
                total_doc_tags = db.query(DocumentTag).count()
                print(f"📊 DB Stats: {total_tags} tags, {total_doc_tags} document-tag links")
                
                # Get tags for this document
                tags_query = db.query(Tag).join(
                    DocumentTag, Tag.id == DocumentTag.tag_id
                ).filter(
                    DocumentTag.document_id == doc.id
                ).all()
                
                print(f"🔍 Tags query returned {len(tags_query)} results")
                
                # Extract tag names
                tag_names = []
                for j, tag in enumerate(tags_query):
                    if tag and tag.name:
                        print(f"   Tag {j+1}: {tag.name} (ID: {tag.id})")
                        tag_names.append(tag.name)
                    else:
                        print(f"   Tag {j+1}: None or empty")
                
                print(f"🏷️  Found {len(tag_names)} tags: {tag_names}")
                
                # ✅ ONLY INCLUDE FILES WITH TAGS
                if not tag_names:
                    print(f"   ⏭️ Skipping - no tags")
                    continue
                
                print(f"✅ Adding to templates")
                
                # Add all tags to set for dropdown
                for tag in tag_names:
                    all_tags_set.add(tag)
                
                # Filter by search
                if search and search.strip():
                    search_lower = search.lower()
                    file_name_lower = file.get('name', '').lower()
                    tags_lower = [t.lower() for t in tag_names]
                    
                    if search_lower not in file_name_lower and not any(search_lower in t for t in tags_lower):
                        print(f"   ⏭️ Skipping - doesn't match search: {search}")
                        continue
                
                # Filter by practice area
                if practice_area and practice_area.strip():
                    practice_area_lower = practice_area.lower()
                    tags_lower = [t.lower() for t in tag_names]
                    if not any(practice_area_lower in t for t in tags_lower):
                        print(f"   ⏭️ Skipping - doesn't match practice area: {practice_area}")
                        continue
                
                # Get owner name
                owner_name = "Unknown"
                owners_list = file.get("owners", [])
                if owners_list and len(owners_list) > 0:
                    first_owner = owners_list[0]
                    owner_name = first_owner.get("displayName", "Unknown")
                
                # Add to templates
                templates.append({
                    "id": file_id,
                    "name": file.get('name', 'Untitled'),
                    "title": file.get('name', 'Untitled'),
                    "owner": owner_name,
                    "modifiedTime": file.get("modifiedTime"),
                    "size": int(file.get("size", 0)),
                    "mimeType": mime_type,
                    "aiTags": tag_names,
                    "tagCount": len(tag_names),
                    "fileUrl": file.get("webViewLink"),
                    "type": "document"
                })
            
            except Exception as file_error:
                print(f"⚠️ Error processing file: {file_error}")
                import traceback
                traceback.print_exc()
                continue
        
        # Convert tags set to sorted list
        practice_areas = sorted(list(all_tags_set))
        
        print(f"\n✅ Templates: {len(templates)} files | Practice Areas: {len(practice_areas)}")
        print(f"📂 ====== TEMPLATES DEBUG END ======\n")
        
        return {
            "templates": templates,
            "practice_areas": practice_areas,
            "total": len(templates)
        }
        
    except Exception as e:
        print(f"❌ Templates error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
    
@router.get("/debug/db-tags")
async def debug_db_tags(db: Session = Depends(get_db)):
    """Debug endpoint to check tags in database"""
    try:
        from app.models.tag import Tag, DocumentTag
        from app.models.document import Document
        
        # Count totals
        total_tags = db.query(Tag).count()
        total_doc_tags = db.query(DocumentTag).count()
        total_docs = db.query(Document).count()
        
        # Get some sample data
        tags = db.query(Tag).limit(10).all()
        doc_tags = db.query(DocumentTag).limit(10).all()
        
        return {
            "stats": {
                "total_tags": total_tags,
                "total_document_tags": total_doc_tags,
                "total_documents": total_docs
            },
            "sample_tags": [{"id": t.id, "name": t.name} for t in tags],
            "sample_document_tags": [
                {"id": dt.id, "document_id": dt.document_id, "tag_id": dt.tag_id} 
                for dt in doc_tags
            ]
        }
    except Exception as e:
        return {"error": str(e)}

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

def format_file_size(bytes_size):
    """Format bytes to human-readable size"""
    if not bytes_size:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"