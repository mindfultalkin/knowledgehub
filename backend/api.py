from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Optional, List
from sqlalchemy.orm import Session
import os
import json
from models.metadata import DocumentTag
from models.metadata import DocumentChunk, VectorEmbedding
from models.metadata import Document, DocumentTag, Tag
from models.metadata import PracticeArea, SubPracticeArea  # ADD THIS



# Import config FIRST
import config

#add note here
from fastapi import Body
from googleapiclient.http import MediaInMemoryUpload
from services.drive_ingestion import DriveIngestionService

# Then import database
from database import get_db

# Then import other modules
from google_drive import GoogleDriveClient
from tagging import SimpleTagger
from document_processor import DocumentProcessor
from simple_search import SimpleTextSearch
from services.drive_ingestion import DriveIngestionService
from models import Document

# CLAUSES THESE IMPORTS
from services.clause_extractor import ClauseExtractor
from models.clauses import DocumentClause, ClauseLibrary
import asyncio

from pydantic import BaseModel
from models import Document, DocumentClause
from database import SessionLocal
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException
from services.risk_scoring import score_contract
from pydantic import BaseModel


router = APIRouter(prefix="/api")



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

class TagUpdateRequest(BaseModel):
    tag: str


def _load_tags_from_doc(doc, db: Session):
    """
    Load tag NAMES for a document from DocumentTag/Tag tables.
    """
    doc_tags = db.query(DocumentTag, Tag).join(
        Tag, DocumentTag.tag_id == Tag.id
    ).filter(
        DocumentTag.document_id == doc.id
    ).all()

    return [tag.name for doc_tag, tag in doc_tags]


def _save_tags_to_doc(doc, tag_names, db: Session):
    """
    Replace current tags with provided tag_names list.
    Safe version: handles errors and rolls back.
    """
    try:
        db.query(DocumentTag).filter(DocumentTag.document_id == doc.id).delete()
        db.flush()

        for name in tag_names:
            clean = name.strip()
            if not clean:
                continue

            tag_obj = db.query(Tag).filter(Tag.name == clean).first()
            if not tag_obj:
                tag_obj = Tag(name=clean, category="custom")
                db.add(tag_obj)
                db.flush()

            link = DocumentTag(document_id=doc.id, tag_id=tag_obj.id)
            db.add(link)

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"❌ Tag save error for document {doc.id}: {e}")
        raise





# Only import dotenv in non-production
if os.getenv("VERCEL_ENV") != "production":
    try:
        from dotenv import set_key
    except ImportError:
        set_key = None


# Initialize router
router = APIRouter()

try:
    drive_client = GoogleDriveClient()
    
    # Initialize SimpleTagger WITHOUT parameters (it will use content-based tagging internally)
    from tagging import SimpleTagger
    tagger = SimpleTagger()
    
    doc_processor = DocumentProcessor(drive_client)             # <-- NO db parameter
    simple_searcher = SimpleTextSearch(drive_client)

    if os.getenv("VERCEL_ENV") != "production":
        drive_client.load_credentials()
    else:
        drive_client.load_credentials()
except Exception as e:
    print(f"⚠️ Warning: Could not initialize clients: {e}")
    drive_client = None
    tagger = None
    doc_processor = None
    nlp_engine = None
    simple_searcher = None



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

def get_current_user_email():
    """
    Get the currently logged-in user's email from Google Drive
    """
    if not drive_client or not drive_client.creds:
        return None
    
    try:
        # Use About API to get current user info
        about = drive_client.service.about().get(fields='user').execute()
        user_email = about['user']['emailAddress']
        return user_email
    except Exception as e:
        print(f"⚠️ Error getting current user: {e}")
        return None

async def trigger_post_auth_extraction():
    """
    Trigger clause extraction after successful authentication
    """
    try:
        print("🔄 Triggering post-auth clause extraction...")
        # Import here to avoid circular imports
        from services.clause_extractor import ClauseExtractor
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            # Your extraction logic here
            print("✅ Post-auth extraction completed")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ Post-auth extraction failed: {e}")


# ==================== BASIC ROUTES ====================


@router.get("/")
async def root():
    return {
        "message": "Knowledge Hub Backend API",
        "version": "1.0.0",
        "authenticated": drive_client.creds is not None if drive_client else False,
        "environment": os.getenv("VERCEL_ENV", "local"),
        "api_base_url": config.SERVICE_API_BASE_URL,
        "frontend_url": config.FRONTEND_URL,
        "redirect_uri": config.GOOGLE_REDIRECT_URIS,
        "status": "running"
    }


@router.get("/health")
async def health():
    return {
        "status": "healthy",
        "env": os.getenv("VERCEL_ENV", "local"),
        "GOOGLE_CLIENT_ID_loaded": bool(os.getenv("GOOGLE_CLIENT_ID")),
        "drive_client_available": drive_client is not None,
        "tagger_available": tagger is not None,
        
        "simple_searcher_available": simple_searcher is not None,
        "doc_processor_available": doc_processor is not None,
        "redirect_uri": config.GOOGLE_REDIRECT_URIS
    }


# ==================== DATABASE ROUTES ====================


@router.get("/db/health")
async def db_health_check(db: Session = Depends(get_db)):
    """
    Check database health and statistics
    """
    try:
        # Count documents
        doc_count = db.query(Document).count()
        
        return {
            "database_connected": True,
            "database_name": config.MYSQL_DATABASE,
            "database_host": config.MYSQL_HOST,
            "total_documents": doc_count,
            "status": "healthy"
        }
    except Exception as e:
        return {
            "database_connected": False,
            "error": str(e),
            "status": "unhealthy"
        }
#==================== GOOGLE DRIVE SYNC ROUTES ====================


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


@router.get("/documents")
async def get_all_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """
    Get all documents from database with pagination - FILTERED BY CURRENT USER
    """
    try:
        # ✅ Get current user's email (FIXED)
        current_user = get_current_user_email()
        
        if not current_user:
            # If not authenticated, return empty list
            return {
                "documents": [],
                "total": 0,
                "skip": skip,
                "limit": limit,
                "current_user": None,
                "message": "Not authenticated or could not identify user"
            }
        
        print(f"📧 Fetching documents for user: {current_user}")
        
        # ✅ Filter documents by current user's account
        documents = db.query(Document).filter(
            Document.account_email == current_user
        ).offset(skip).limit(limit).all()
        
        total = db.query(Document).filter(
            Document.account_email == current_user
        ).count()
        
        print(f"📊 Found {total} documents for {current_user}")
        
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
                    "account_email": doc.account_email  # Show which account owns it
                }
                for doc in documents
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
            "current_user": current_user  # Show current logged-in user
        }
    except Exception as e:
        import traceback
        print(f"❌ Error: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}/tags")
async def get_document_tags(document_id: str, db: Session = Depends(get_db)):
    try:
        doc = _get_document_by_any_id(db, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # 1) read saved tags from metadata tables
        tags = _load_tags_from_doc(doc, db)

        # 2) if none yet, seed from SimpleTagger once
        if not tags and tagger:
            auto_tags = tagger.generate_tags(doc.title or "", doc.mime_type, None)
            tags = auto_tags
            _save_tags_to_doc(doc, tags, db)

        return {"document_id": document_id, "tags": tags}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/tags/add")
async def add_document_tag(document_id: str, payload: TagUpdateRequest, db: Session = Depends(get_db)):
    try:
        tag = (payload.tag or "").strip()
        if not tag:
            raise HTTPException(status_code=400, detail="Tag cannot be empty")

        doc = _get_document_by_any_id(db, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        tags = _load_tags_from_doc(doc, db)
        if tag not in tags:
            tags.append(tag)
            _save_tags_to_doc(doc, tags, db)

        return {"success": True, "document_id": document_id, "tags": tags}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/tags/remove")
async def remove_document_tag(document_id: str, payload: TagUpdateRequest, db: Session = Depends(get_db)):
    try:
        tag = (payload.tag or "").strip()
        if not tag:
            raise HTTPException(status_code=400, detail="Tag cannot be empty")

        doc = _get_document_by_any_id(db, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        tags = _load_tags_from_doc(doc, db)
        if tag in tags:
            tags.remove(tag)
            _save_tags_to_doc(doc, tags, db)

        return {"success": True, "document_id": document_id, "tags": tags}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))




# ==================== GOOGLE AUTH ROUTES ====================


@router.get("/auth/google")
async def google_auth():
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    
    try:
        print(f"🔗 Generating auth URL with redirect URI: {config.GOOGLE_REDIRECT_URIS}")
        auth_url, state = drive_client.get_authorization_url(config.GOOGLE_REDIRECT_URIS)
        return {"auth_url": auth_url}
    except Exception as e:
        print(f"❌ Error in google_auth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/oauth2callback")
async def oauth2callback(code: str, state: str = None):
    """OAuth callback - FIXED: Database is now optional"""
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    
    try:
        print(f"🔗 Exchanging code with redirect URI: {config.GOOGLE_REDIRECT_URIS}")
        drive_client.exchange_code_for_credentials(code, config.GOOGLE_REDIRECT_URIS)
        print("✅ OAuth credentials obtained successfully")
        
        # Try database sync, but don't fail if database is unavailable
        try:
            from database import get_db_context
            from services.drive_ingestion import DriveIngestionService
            
            print("🔄 Attempting auto-sync...")
            with get_db_context() as db:
                ingestion_service = DriveIngestionService(drive_client, db)
                stats = ingestion_service.sync_all_files()
                print(f"✅ Auto-sync completed: {stats}")
                
            # Trigger clause extraction
            print("🔄 Triggering clause extraction...")
            asyncio.create_task(trigger_post_auth_extraction())
            
        except Exception as sync_error:
            print(f"⚠️ Auto-sync failed (non-critical): {sync_error}")
            # Continue anyway - user is authenticated
        
        return RedirectResponse(url=f"{config.FRONTEND_URL}?auth=success")
        
    except Exception as e:
        print(f"❌ OAuth callback error: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=f"{config.FRONTEND_URL}?auth=error&message={str(e)}")


@router.post("/auth/logout")
async def logout():
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    
    try:
        if os.getenv("VERCEL_ENV") != "production" and set_key:
            env_file = os.path.join(os.path.dirname(__file__), ".env")
            set_key(env_file, "GOOGLE_ACCESS_TOKEN", "")
            set_key(env_file, "GOOGLE_REFRESH_TOKEN", "")
            set_key(env_file, "GOOGLE_TOKEN_EXPIRY", "")

        if drive_client:
            drive_client.creds = None
            drive_client.service = None

        return {"message": "Logged out successfully"}
    except Exception as e:
        print(f"❌ Error during logout: {e}")
        return {"message": "Logout completed (with minor issues)"}


@router.get("/auth/status")
async def auth_status():
    if not drive_client:
        return {"authenticated": False, "error": "Drive client not initialized"}
    
    is_authenticated = drive_client.creds is not None
    user_info = None

    if is_authenticated:
        try:
            about = drive_client.get_about()
            user_info = {
                "email": about["user"]["emailAddress"],
                "displayName": about["user"]["displayName"],
            }
        except Exception as e:
            print(f"Error getting user info: {e}")

    return {"authenticated": is_authenticated, "user": user_info}


# ==================== LEGACY DRIVE ROUTES ====================


@router.get("/drive/files")
async def get_files(
    page_size: int = 50, 
    page_token: Optional[str] = None, 
    query: Optional[str] = None,
    db: Session = Depends(get_db)  # ✅ ADDED MISSING DB
):
    """
    List files from Google Drive + ADD TAGS from document_tags table
    """
    if not drive_client:
        raise HTTPException(status_code=500, detail="Services not initialized")
    
    try:
        if not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        # ✅ Get current user's email
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
            # ✅ LOOKUP DOCUMENT IN DB BY DRIVE FILE ID
            doc = db.query(Document).filter(
                Document.drive_file_id == file["id"]
            ).first()
            
            # ✅ GET TAGS FROM document_tags table
            ai_tags = []
            tag_count = 0
            if doc:
                doc_tags = db.query(DocumentTag).filter(
                    DocumentTag.document_id == doc.id
                ).join(Tag).all()
                ai_tags = [dt.tag.name for dt in doc_tags]
                tag_count = len(ai_tags)
                print(f"🏷️ Found {tag_count} tags for {file['name']}")

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
                "aiTags": ai_tags,        # ✅ FILLED WITH REAL TAGS
                "tagCount": tag_count,    # ✅ NEW FIELD
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


@router.get("/tags")
async def get_all_tags():
    """Get all available tags"""
    if not tagger:
        raise HTTPException(status_code=500, detail="Tagger not initialized")
    
    return {
        "categories": list(tagger.CATEGORIES.keys()),
        "contentTags": list(tagger.CONTENT_KEYWORDS.keys())
    }

# ==================== SIMPLE SEARCH ROUTES ====================


@router.get("/search/simple")
async def simple_text_search(query: str, db: Session = Depends(get_db)):
    """Simple exact text search - FROM DATABASE (filtered by user)"""
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        # ✅ Get current user email
        current_user = None
        try:
            about = drive_client.service.about().get(fields='user').execute()
            current_user = about['user']['emailAddress']
            print(f"🔍 Simple search for user: {current_user}")
        except Exception as e:
            print(f"⚠️ Could not get user: {e}")
            return {"query": query, "results": [], "error": "Not authenticated"}
        
        # ✅ Search in DATABASE (filtered by current user)
        print(f"🔍 SIMPLE SEARCH: '{query}' for user {current_user}")
        
        documents = db.query(Document).filter(
            Document.account_email == current_user,
            Document.title.ilike(f'%{query}%')
        ).all()
        
        formatted_results = []
        for doc in documents:
            formatted_results.append({
                'id': doc.id,
                'name': doc.title,
                'mimeType': doc.mime_type,
                'owner': doc.owner_name,
                'modifiedTime': doc.modified_at.isoformat() if doc.modified_at else '',
                'webViewLink': doc.file_url,
                'size': str(doc.size_bytes) if doc.size_bytes else '0',
                'content_preview': '',
                'search_type': 'exact_match',
                'currentUser': current_user
            })
        
        print(f"✅ Simple search found {len(formatted_results)} results for {current_user}")
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "search_type": "exact_text_match",
            "currentUser": current_user
        }
        
    except Exception as e:
        print(f"❌ Simple search error: {e}")
        import traceback
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Simple search failed: {str(e)}")

# ==================== DEBUG ROUTES ====================


@router.get("/debug/simple-search")
async def debug_simple_search():
    """Debug simple search status"""
    if not simple_searcher:
        return {"simple_search_loaded": False, "error": "Simple search not initialized"}
    
    return {
        "simple_search_loaded": simple_searcher.is_loaded,
        "documents_loaded": len(simple_searcher.documents),
        "drive_connected": drive_client.creds is not None if drive_client else False
    }


@router.get("/debug/oauth-config")
async def debug_oauth_config():
    """Debug OAuth configuration"""
    return {
        "environment": os.getenv("VERCEL_ENV", "local"),
        "redirect_uri": config.GOOGLE_REDIRECT_URIS,
        "api_base_url": config.SERVICE_API_BASE_URL,
        "frontend_url": config.FRONTEND_URL,
        "drive_authenticated": drive_client.creds is not None if drive_client else False
    }

@router.get("/auth/account-info")
async def get_account_info():
    """
    Get current logged-in account information
    """
    if not drive_client or not drive_client.creds:
        return {"authenticated": False}
    
    try:
        about = drive_client.service.users().get(userId='me').execute()
        return {
            "authenticated": True,
            "email": about.get('emailAddress'),
            "name": about.get('displayName'),
            "user_id": about.get('permissionId')
        }
    except Exception as e:
        return {"authenticated": False, "error": str(e)}

@router.get("/debug/user")
async def debug_current_user():
    """
    Debug endpoint to check current user
    """
    if not drive_client:
        return {"error": "Drive client not initialized"}
    
    if not drive_client.creds:
        return {"error": "Not authenticated"}
    
    try:
        about = drive_client.service.about().get(fields='user').execute()
        return {
            "success": True,
            "user": about['user']
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

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



# ============================================================
# CLAUSE EXTRACTION ENDPOINTS (CORRECT ORDER)
# ============================================================

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
async def get_library_clauses(db: Session = Depends(get_db)):
    """
    Get all saved clauses from library
    """
    try:
        clauses = db.query(ClauseLibrary).order_by(
            ClauseLibrary.created_at.desc()
        ).all()
        
        clause_list = [
            {
                'id': c.id,
                'title': c.clause_title,
                'section_number': c.section_number,
                'content_preview': c.clause_content[:200] + '...' if len(c.clause_content) > 200 else c.clause_content,
                'source_document': c.source_document_name,
                'saved_by': c.saved_by,
                'created_at': c.created_at.isoformat() if c.created_at else None
            }
            for c in clauses
        ]
        
        return JSONResponse(
            content={
                "count": len(clause_list),
                "clauses": clause_list
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{file_id}/extract-clauses")
async def extract_clauses(file_id: str, db: Session = Depends(get_db)):
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        document = _get_document_by_any_id(db, file_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        print(f"📄 Extracting clauses from: {document.title}")
        
        # Extract content using existing content extractor
        from services.universal_content_extractor import UniversalContentExtractor
        content_extractor = UniversalContentExtractor(drive_client)
        content = content_extractor.extract_content(file_id, document.mime_type or '')
        
        if not content:
            return {
                "message": "No content found in document",
                "count": 0,
                "clauses": []
            }
        
        # Extract clauses from content
        extractor = ClauseExtractor()
        clauses = extractor.extract_clauses_from_content(content)
        
        if not clauses:
            return {
                "message": "No clauses found",
                "count": 0,
                "clauses": []
            }
        
        # Clear old cached clauses for this document
        db.query(DocumentClause).filter(DocumentClause.document_id == file_id).delete()
        db.commit()
        
        # Save to document_clauses table (temporary cache)
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
        print(f"✅ Saved {len(clauses)} clauses to cache")
        
        # Return clause list for display
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
            saved_by=document.owner_email if document else None
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


# 3️⃣ GENERIC ROUTE LAST (with path parameter - must be at the end)
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



# ============================================================
# QL PARTNERS TEMPLATE LIBRARY & GROUPED SEARCH
# ============================================================

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

@router.post("/templates/cleanup-prod")
async def cleanup_prod(db: Session = Depends(get_db)):
    """🧹 Railway: Delete deleted Drive files"""
    # Find orphans: tags but no valid Drive data
    orphans = db.query(Document).filter(
        Document.drive_file_id.is_(None),
        Document.size_bytes <= 0,
        Document.file_url.is_(None)
    ).delete(synchronize_session=False)
    db.commit()
    return {"cleaned": orphans}


@router.get("/templates")
async def list_templates(
    practice_area: str = None, 
    search: str = None,
    db: Session = Depends(get_db)
):
    """Works Local + Railway: Drive verification + DB fallback"""
    
    templates = []
    
    try:
        # ✅ TRY DRIVE API FIRST (live files only)
        if drive_client and drive_client.creds:
            results = drive_client.list_files(100, None, None)
            drive_files = results.get("files", [])
            
            for file in drive_files:
                doc = db.query(Document).filter(
                    Document.drive_file_id == file["id"]
                ).first()
                
                if doc:
                    doc_tags = db.query(Tag.name).join(DocumentTag).filter(
                        DocumentTag.document_id == doc.id
                    ).all()
                    
                    if doc_tags:  # Tags only
                        ai_tags = [tag[0] for tag in doc_tags]
                        
                        if (not search or search.lower() in file["name"].lower()) and \
                           (not practice_area or any(practice_area.lower() in tag.lower() for tag in ai_tags)):
                            templates.append({
                                "id": file["id"],
                                "name": file["name"],
                                "title": file["name"],
                                "owner": file.get("owners", [{}])[0].get("displayName", "Unknown"),
                                "modifiedTime": file.get("modifiedTime"),
                                "size": file.get("size", 0),
                                "mimeType": file.get("mimeType"),
                                "aiTags": ai_tags,
                                "tagCount": len(ai_tags),
                                "file_url": file.get("webViewLink"),
                                "type": "document"
                            })
            print(f"Drive API: {len(templates)} files")
            
    except Exception as e:
        print(f"Drive API failed: {e} - using DB fallback")
    
    # ✅ DB FALLBACK (Railway-safe)
    if len(templates) == 0:
        query = db.query(Document).join(DocumentTag).distinct()
        docs = query.filter(
            Document.file_url.isnot(None),
            Document.size_bytes > 5000,
            ~Document.title.ilike('%deleted%'),
            ~Document.title.ilike('%temp%')
        ).limit(50).all()
        
        for doc in docs:
            doc_tags = db.query(Tag.name).join(DocumentTag).filter(
                DocumentTag.document_id == doc.id
            ).all()
            
            templates.append({
                "id": str(doc.id),
                "name": doc.title,
                "title": doc.title,
                "owner": doc.owner_name or "Unknown",
                "modifiedTime": doc.modified_at.isoformat() if doc.modified_at else None,
                "size": doc.size_bytes or 0,
                "mimeType": doc.mime_type or "",
                "aiTags": [tag[0] for tag in doc_tags],
                "tagCount": len(doc_tags),
                "file_url": doc.file_url,
                "type": "document"
            })
        print(f"DB fallback: {len(templates)} files")
    
    # All tags
    practice_areas = sorted(set(tag[0] for tag in db.query(Tag.name.distinct()).all()))
    
    print(f"Templates FINAL: {len(templates)}")
    return {
        "templates": templates,
        "practice_areas": practice_areas,
        "total": len(templates)
    }




# ==================== HELPER FUNCTION ====================

def format_file_size(bytes_size):
    """Format bytes to human-readable size"""
    if not bytes_size:
        return "0 B"
    
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"