"""
Search controllers
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from sqlalchemy.orm import Session
import re

# Import models and services
from database import get_db
from app.models.document import Document
from app.models.tag import Tag
from app.models.practice_area import PracticeArea, SubPracticeArea
from app.services.google_drive_service import GoogleDriveClient
from app.services.search_service import SimpleTextSearch
from app.services.tag_service import SimpleTagger
from app.controllers.auth_controller import get_current_user_email

router = APIRouter()

# Initialize services
try:
    drive_client = GoogleDriveClient()
    tagger = SimpleTagger()
    simple_searcher = SimpleTextSearch(drive_client)
except Exception as e:
    print(f"⚠️ Warning: Could not initialize services: {e}")
    drive_client = None
    tagger = None
    simple_searcher = None

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

@router.get("/tags")
async def get_all_tags():
    """Get all available tags"""
    if not tagger:
        raise HTTPException(status_code=500, detail="Tagger not initialized")
    
    return {
        "categories": list(tagger.CATEGORIES.keys()),
        "contentTags": list(tagger.CONTENT_KEYWORDS.keys())
    }
