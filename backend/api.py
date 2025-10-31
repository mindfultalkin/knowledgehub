from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from typing import Optional
import os

from config import (
    ALLOWED_ORIGINS, SERVICE_API_BASE_URL,
    FRONTEND_URL, BACKEND_HOST, BACKEND_PORT
)
from google_drive import GoogleDriveClient
from tagging import SimpleTagger

# Only import dotenv in non-production
if os.getenv("VERCEL_ENV") != "production":
    try:
        from dotenv import set_key
    except ImportError:
        set_key = None

# Initialize router
router = APIRouter()

# Initialize clients
try:
    drive_client = GoogleDriveClient()
    tagger = SimpleTagger()
    
    if os.getenv("VERCEL_ENV") != "production":
        drive_client.load_credentials()
except Exception as e:
    print(f"⚠️ Warning: Could not initialize clients: {e}")
    drive_client = None
    tagger = None

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
        "tagger_available": tagger is not None
    }

@router.get("/auth/google")
async def google_auth():
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    
    try:
        redirect_uri = f"{SERVICE_API_BASE_URL}/api/oauth2callback"
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
        redirect_uri = f"{SERVICE_API_BASE_URL}/api/oauth2callback"
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
