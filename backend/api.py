from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional
import os

from config import (
    ALLOWED_ORIGINS, SERVICE_API_BASE_URL,
    FRONTEND_URL, BACKEND_HOST, BACKEND_PORT, MODELS_DIR
)
from google_drive import GoogleDriveClient
from tagging import SimpleTagger
from nlp_search import NLPSearchEngine
from document_processor import DocumentProcessor
from simple_search import SimpleTextSearch

# Only import dotenv in non-production
if os.getenv("VERCEL_ENV") != "production":
    try:
        from dotenv import set_key
    except ImportError:
        set_key = None

# Initialize router
router = APIRouter()

# Initialize ALL clients - CRITICAL FIX
try:
    drive_client = GoogleDriveClient()
    tagger = SimpleTagger()
    doc_processor = DocumentProcessor(drive_client)
    nlp_engine = NLPSearchEngine()
    simple_searcher = SimpleTextSearch(drive_client)
    
    if os.getenv("VERCEL_ENV") != "production":
        drive_client.load_credentials()
    else:
        # In production, try to load credentials from environment
        drive_client.load_credentials()
except Exception as e:
    print(f"⚠️ Warning: Could not initialize clients: {e}")
    drive_client = None
    tagger = None
    doc_processor = None
    nlp_engine = None
    simple_searcher = None

# Helper function for content preview
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

# ==================== BASIC ROUTES ====================

@router.get("/")
async def root():
    return {
        "message": "Knowledge Hub Backend API",
        "version": "1.0.0",
        "authenticated": drive_client.creds is not None if drive_client else False,
        "environment": os.getenv("VERCEL_ENV", "local"),
        "api_base_url": SERVICE_API_BASE_URL,
        "frontend_url": FRONTEND_URL,
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
        "nlp_engine_available": nlp_engine is not None,
        "simple_searcher_available": simple_searcher is not None,
        "doc_processor_available": doc_processor is not None
    }

@router.get("/auth/google")
async def google_auth():
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    
    try:
        redirect_uri = f"{SERVICE_API_BASE_URL}/oauth2callback"
        auth_url, _ = drive_client.get_authorization_url(redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        print(f"❌ Error in google_auth: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/oauth2callback")
async def oauth2callback(code: str):
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    
    try:
        redirect_uri = f"{SERVICE_API_BASE_URL}/oauth2callback"
        drive_client.exchange_code_for_credentials(code, redirect_uri)
        return RedirectResponse(url=f"{FRONTEND_URL}?auth=success")
    except Exception as e:
        print(f"❌ Error in oauth2callback: {e}")
        return RedirectResponse(url=f"{FRONTEND_URL}?auth=error&message={str(e)}")

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

@router.get("/drive/files")
async def get_files(page_size: int = 50, page_token: Optional[str] = None, query: Optional[str] = None):
    """List files from Google Drive"""
    if not drive_client or not tagger:
        raise HTTPException(status_code=500, detail="Services not initialized")
    
    try:
        if not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        results = drive_client.list_files(page_size, page_token, query)

        files = []
        for file in results.get("files", []):
            tags = tagger.generate_tags(file["name"], file.get("mimeType"), file.get("description"))
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
            }
            files.append(file_data)

        return {"files": files, "nextPageToken": results.get("nextPageToken"), "totalCount": len(files)}

    except Exception as e:
        print(f"❌ Error getting files: {e}")
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

# ==================== NLP ROUTES ====================

@router.post("/nlp/train")
async def train_nlp_model():
    """Train NLP model on all Google Drive files"""
    try:
        print("🔄 Starting NLP training...")
        
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not doc_processor:
            raise HTTPException(status_code=500, detail="Document processor not initialized")
        
        if not nlp_engine:
            raise HTTPException(status_code=500, detail="NLP engine not initialized")
        
        # Get all files
        print("📁 Fetching files from Google Drive...")
        files_response = drive_client.list_files(page_size=1000)
        files = files_response.get('files', [])
        print(f"✅ Found {len(files)} files total")
        
        # Process files and extract content
        print("🔍 Processing files and extracting content...")
        documents = doc_processor.prepare_documents_for_nlp(files)
        
        print(f"📄 Successfully processed {len(documents)} documents with content")
        
        if not documents:
            return {
                "message": "No processable documents found", 
                "total_files": len(files),
                "processed_files": len(documents)
            }
        
        # Train NLP model
        print("🤖 Training NLP model with embeddings...")
        nlp_engine.create_embeddings(documents)
        
        # Save model
        model_path = os.path.join(MODELS_DIR, "nlp_search_model.pkl")
        nlp_engine.save_model(model_path)
        
        print("🎉 NLP training completed successfully!")
        
        return {
            "message": "NLP model trained successfully",
            "total_files": len(files),
            "documents_processed": len(documents),
            "model_saved": True
        }
        
    except Exception as e:
        print(f"❌ Training failed with error: {str(e)}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")

@router.get("/nlp/search")
async def nlp_search(query: str, top_k: int = 10):
    """Search using NLP semantic search"""
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not nlp_engine:
            raise HTTPException(status_code=500, detail="NLP engine not initialized")
        
        if not nlp_engine.is_trained:
            # Try to load existing model
            model_path = os.path.join(MODELS_DIR, "nlp_search_model.pkl")
            if os.path.exists(model_path):
                nlp_engine.load_model(model_path)
            else:
                raise HTTPException(status_code=400, detail="NLP model not trained. Please train first.")
        
        # Perform search
        results = nlp_engine.search(query, top_k)
        
        # Format results for frontend
        formatted_results = []
        for result in results:
            doc = result['document']
            formatted_results.append({
                'id': doc['id'],
                'name': doc['name'],
                'mimeType': doc.get('mimeType', ''),
                'score': result['score'],
                'relevance': result['relevance'],
                'snippet': doc.get('content', '')[:200] + '...' if doc.get('content') else '',
                'owner': doc.get('owner', 'Unknown'),
                'modifiedTime': doc.get('modifiedTime', ''),
                'webViewLink': doc.get('webViewLink', ''),
                'size': doc.get('size', '0')
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/nlp/status")
async def nlp_status():
    """Get NLP model status"""
    if not nlp_engine:
        return {"is_trained": False, "error": "NLP engine not initialized"}
    
    return {
        "is_trained": nlp_engine.is_trained,
        "documents_indexed": len(nlp_engine.documents) if nlp_engine.is_trained else 0,
        "model_ready": nlp_engine.is_trained
    }

# ==================== SIMPLE SEARCH ROUTES ====================

@router.get("/search/simple")
async def simple_text_search(query: str):
    """Simple exact text search - works immediately"""
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not simple_searcher:
            raise HTTPException(status_code=500, detail="Simple search not initialized")
        
        # Simple search loads documents directly, no need for NLP training
        results = simple_searcher.search_documents(query)
        
        formatted_results = []
        for result in results:
            doc = result['document']
            formatted_results.append({
                'id': doc['id'],
                'name': doc['name'],
                'mimeType': doc.get('mimeType', ''),
                'owner': doc.get('owner', 'Unknown'),
                'modifiedTime': doc.get('modifiedTime', ''),
                'webViewLink': doc.get('webViewLink', ''),
                'size': doc.get('size', '0'),
                'content_preview': get_content_preview(doc.get('content', ''), query),
                'search_type': 'exact_match'
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "search_type": "exact_text_match"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Simple search failed: {str(e)}")

@router.get("/search/ai")
async def ai_semantic_search(query: str, top_k: int = 10):
    """AI semantic search (your existing NLP search)"""
    try:
        if not drive_client or not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")
        
        if not nlp_engine:
            raise HTTPException(status_code=500, detail="NLP engine not initialized")
        
        if not nlp_engine.is_trained:
            model_path = os.path.join(MODELS_DIR, "nlp_search_model.pkl")
            if os.path.exists(model_path):
                nlp_engine.load_model(model_path)
            else:
                raise HTTPException(status_code=400, detail="NLP model not trained")
        
        results = nlp_engine.search(query, top_k)
        
        formatted_results = []
        for result in results:
            doc = result['document']
            formatted_results.append({
                'id': doc['id'],
                'name': doc['name'],
                'mimeType': doc.get('mimeType', ''),
                'score': result['score'],
                'relevance': result['relevance'],
                'owner': doc.get('owner', 'Unknown'),
                'modifiedTime': doc.get('modifiedTime', ''),
                'webViewLink': doc.get('webViewLink', ''),
                'size': doc.get('size', '0'),
                'snippet': doc.get('content', '')[:200] + '...',
                'search_type': 'ai_semantic'
            })
        
        return {
            "query": query,
            "results": formatted_results,
            "total_results": len(formatted_results),
            "search_type": "ai_semantic"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI search failed: {str(e)}")

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