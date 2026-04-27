from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
import os
import json
import asyncio
from datetime import datetime
from pydantic import BaseModel

import config
from database import get_db

# Models - Split correctly
from models.metadata import (
    Document, DocumentTag, Tag, DocumentChunk, VectorEmbedding,
    PracticeArea, SubPracticeArea, ContentType
)

from models.clauses import DocumentClause, ClauseLibrary, ClauseTag

# Services
from services.drive_ingestion import DriveIngestionService
from services.clause_extractor import ClauseExtractor
from services.universal_content_extractor import UniversalContentExtractor

# ✅ REMOVED: score_contract direct import — now handled by risk_scoring router
# from services.risk_scoring import score_contract  ← DELETE THIS LINE

# Other modules
from google_drive import GoogleDriveClient
from tagging import SimpleTagger
from document_processor import DocumentProcessor
from simple_search import SimpleTextSearch
from googleapiclient.http import MediaInMemoryUpload
from core.google_client import drive_client

# Controllers
from controllers.auth_controller import router as auth_router
from controllers.system_controller import router as system_router
from controllers.document_controller import router as document_router
from controllers.clause_controller import router as clause_router
from controllers.user_controller import router as user_router
from controllers.Note_controller import router as note_router   
# ✅ NEW: Import the dedicated risk scoring router
from services.risk_scoring import router as risk_router

# Initialize router
router = APIRouter()
router.include_router(auth_router)
router.include_router(system_router)
router.include_router(document_router)
router.include_router(clause_router)
router.include_router(user_router)
router.include_router(risk_router)
router.include_router(note_router)  # ✅ ADD THIS — mounts /contracts/{id}/risk-score and /risk-analysis/*


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


# ==================== CLAUSE TAG PYDANTIC MODELS ====================

class ClauseTagCreate(BaseModel):
    clause_id: int
    tag_name: str

class ClauseTagRemove(BaseModel):
    clause_id: int
    tag_id: int

class ClauseWithTagsResponse(BaseModel):
    id: int
    clause_title: str
    section_number: str
    content_preview: str
    tags: List[Dict[str, Any]]
    saved_by: str
    created_at: str


def _load_tags_from_doc(doc, db: Session):
    """
    Visible tag names for a document. `source='user_removed'` rows are
    tombstones (the user explicitly removed them); they stay in the
    table to block the auto-tagger but must never appear in any
    user-facing list.
    """
    doc_tags = db.query(DocumentTag, Tag).join(
        Tag, DocumentTag.tag_id == Tag.id
    ).filter(
        DocumentTag.document_id == doc.id,
        (DocumentTag.source != "user_removed") | (DocumentTag.source.is_(None))
    ).all()
    return [tag.name for doc_tag, tag in doc_tags]


def _save_tags_to_doc(doc, tag_names, db: Session):
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


try:
    from tagging import SimpleTagger
    tagger = SimpleTagger()

    doc_processor = DocumentProcessor(drive_client)
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
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if doc:
        return doc
    return db.query(Document).filter(Document.drive_file_id == doc_id).first()


def get_content_preview(content: str, query: str, preview_length: int = 200) -> str:
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
    if not drive_client or not drive_client.creds:
        return None
    try:
        about = drive_client.service.about().get(fields='user').execute()
        return about['user']['emailAddress']
    except Exception as e:
        print(f"⚠️ Error getting current user: {e}")
        return None


async def trigger_post_auth_extraction():
    try:
        print("🔄 Triggering post-auth clause extraction...")
        from services.clause_extractor import ClauseExtractor
        from database import SessionLocal
        db = SessionLocal()
        try:
            print("✅ Post-auth extraction completed")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ Post-auth extraction failed: {e}")


@router.get("/auth/account-info")
async def get_account_info():
    try:
        global drive_client
        if not drive_client or not drive_client.creds:
            return {"authenticated": False}
        about = drive_client.service.about().get(fields='user').execute()
        email = about['user']['emailAddress']
        print(f"📧 Current user: {email}")
        return {
            "authenticated": True,
            "email": email,
            "name": about['user'].get('displayName', '')
        }
    except Exception as e:
        print(f"❌ Auth info error: {e}")
        return {"authenticated": False}


# ==================== GOOGLE DRIVE SYNC ROUTES ====================

@router.post("/sync/drive-full")
async def sync_drive_full(db: Session = Depends(get_db)):
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
    try:
        ingestion_service = DriveIngestionService(drive_client, db)
        stats = ingestion_service.get_sync_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== LEGACY DRIVE ROUTES ====================

@router.get("/drive/files")
async def get_files(
    page_size: int = 50,
    page_token: Optional[str] = None,
    query: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if not drive_client:
        raise HTTPException(status_code=500, detail="Services not initialized")

    try:
        if not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        try:
            about = drive_client.service.about().get(fields='user').execute()
            current_user = about['user']['emailAddress']
            print(f"📧 Loading files for user: {current_user}")
        except Exception as e:
            print(f"⚠️ Could not get current user: {e}")
            current_user = None

        results = drive_client.list_files(page_size, page_token, query)

        files = []
        for file in results.get("files", []):
            doc = _get_document_by_any_id(db, file["id"])

            ai_tags = []
            tag_count = 0
            # Exclude `user_removed` tombstones from every aiTags surface
            # so user removals are honored on the dashboard, header
            # search cache, etc.
            visible = (DocumentTag.source != "user_removed") | (DocumentTag.source.is_(None))
            if doc:
                doc_tags = db.query(DocumentTag).filter(
                    DocumentTag.document_id == doc.id,
                    visible,
                ).join(Tag).all()
                ai_tags = [dt.tag.name for dt in doc_tags]
                tag_count = len(ai_tags)
                print(f"🏷️ Found {tag_count} tags for {file['name']} via doc.id={doc.id}")
            else:
                doc_tags = db.query(DocumentTag).join(Document).join(Tag).filter(
                    Document.drive_file_id == file["id"],
                    visible,
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
                "aiTags": ai_tags,
                "tagCount": tag_count,
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
    if not tagger:
        raise HTTPException(status_code=500, detail="Tagger not initialized")
    return {
        "categories": list(tagger.CATEGORIES.keys()),
        "contentTags": list(tagger.CONTENT_KEYWORDS.keys())
    }


# ==================== SIMPLE SEARCH ROUTES ====================

@router.get("/search/simple")
async def simple_text_search(query: str, db: Session = Depends(get_db)):
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        current_user = None
        try:
            about = drive_client.service.about().get(fields='user').execute()
            current_user = about['user']['emailAddress']
            print(f"🔍 Simple search for user: {current_user}")
        except Exception as e:
            print(f"⚠️ Could not get user: {e}")
            return {"query": query, "results": [], "error": "Not authenticated"}

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
    if not simple_searcher:
        return {"simple_search_loaded": False, "error": "Simple search not initialized"}
    return {
        "simple_search_loaded": simple_searcher.is_loaded,
        "documents_loaded": len(simple_searcher.documents),
        "drive_connected": drive_client.creds is not None if drive_client else False
    }


@router.get("/debug/oauth-config")
async def debug_oauth_config():
    return {
        "environment": os.getenv("VERCEL_ENV", "local"),
        "redirect_uri": config.GOOGLE_REDIRECT_URIS,
        "api_base_url": config.SERVICE_API_BASE_URL,
        "frontend_url": config.FRONTEND_URL,
        "drive_authenticated": drive_client.creds is not None if drive_client else False
    }


@router.get("/debug/user")
async def debug_current_user():
    if not drive_client:
        return {"error": "Drive client not initialized"}
    if not drive_client.creds:
        return {"error": "Not authenticated"}
    try:
        about = drive_client.service.about().get(fields='user').execute()
        return {"success": True, "user": about['user']}
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@router.get("/drive/files-live")
async def get_files_live(
    page_size: int = 50,
    page_token: Optional[str] = None,
    query: Optional[str] = None
):
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    if not tagger:
        raise HTTPException(status_code=500, detail="Tagger not initialized")

    try:
        if not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")

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
                    "source": "google_drive_live"
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


# ============================================================
# QL PARTNERS TEMPLATE LIBRARY & GROUPED SEARCH
# ============================================================

@router.get("/search/grouped")
async def grouped_search(query: str, content_type: str = None, db: Session = Depends(get_db)):
    current_user = get_current_user_email()

    results = {
        "templates": [],
        "clause_sets": [],
        "practice_notes": [],
        "knowledge_materials": [],
        "total": 0
    }

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


# ==================== HELPER FUNCTION ====================

def format_file_size(bytes_size):
    if not bytes_size:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"