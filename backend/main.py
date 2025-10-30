from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from typing import Optional
import os
import sys

# Add backend directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

# Import modules - use absolute imports for Vercel
import config
from google_drive import GoogleDriveClient
from tagging import SimpleTagger

# Only import dotenv functions if not in production
if os.getenv("VERCEL_ENV") != "production":
    from dotenv import set_key

# ----------------------------------------------------
# App Initialization
# ----------------------------------------------------
app = FastAPI(title="Knowledge Hub Backend", version="1.0.0", root_path="/api")

# CORS Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clients
drive_client = GoogleDriveClient()
tagger = SimpleTagger()

# Only load credentials from file if not in production (local development)
if os.getenv("VERCEL_ENV") != "production":
    drive_client.load_credentials()

# ----------------------------------------------------
# Routes
# ----------------------------------------------------
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Knowledge Hub Backend API",
        "version": "1.0.0",
        "authenticated": drive_client.creds is not None,
        "environment": os.getenv("VERCEL_ENV", "local"),
        "api_base_url": config.SERVICE_API_BASE_URL,
        "frontend_url": config.FRONTEND_URL,
    }


# @app.get("/health")
# async def health():
#     return {
#         "status": "healthy",
#         "environment": os.getenv("VERCEL_ENV", "local"),
#         "authenticated": drive_client.creds is not None
#     }
@app.get("/health")
async def health():
    # Debug information for verifying environment variables
    debug_env = {
        "VERCEL_ENV": os.getenv("VERCEL_ENV"),
        "GOOGLE_CLIENT_ID": bool(os.getenv("GOOGLE_CLIENT_ID")),
        "GOOGLE_CLIENT_SECRET": bool(os.getenv("GOOGLE_CLIENT_SECRET")),
        "SERVICE_API_BASE_URL": os.getenv("SERVICE_API_BASE_URL"),
        "FRONTEND_URL": os.getenv("FRONTEND_URL"),
    }

    return {
        "status": "healthy" if all(debug_env.values()) else "env_missing",
        "env_check": debug_env,
    }


@app.get("/auth/google")
async def google_auth():
    """Start Google OAuth flow"""
    try:
        redirect_uri = f"{config.SERVICE_API_BASE_URL}/api/oauth2callback"
        auth_url, _ = drive_client.get_authorization_url(redirect_uri)
        return {"auth_url": auth_url}
    except Exception as e:
        print(f"❌ Error in google_auth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/oauth2callback")
async def oauth2callback(code: str):
    """Handle OAuth callback"""
    try:
        redirect_uri = f"{config.SERVICE_API_BASE_URL}/api/oauth2callback"
        drive_client.exchange_code_for_credentials(code, redirect_uri)

        # Redirect to frontend after successful authentication
        return RedirectResponse(url=f"{config.FRONTEND_URL}?auth=success")

    except Exception as e:
        print(f"❌ Error in oauth2callback: {e}")
        return RedirectResponse(url=f"{config.FRONTEND_URL}?auth=error&message={str(e)}")


@app.post("/auth/logout")
async def logout():
    """Logout and clear saved credentials"""
    try:
        # Only update .env file in local development
        if os.getenv("VERCEL_ENV") != "production":
            env_file = os.path.join(os.path.dirname(__file__), ".env")
            set_key(env_file, "GOOGLE_ACCESS_TOKEN", "")
            set_key(env_file, "GOOGLE_REFRESH_TOKEN", "")
            set_key(env_file, "GOOGLE_TOKEN_EXPIRY", "")

        drive_client.creds = None
        drive_client.service = None

        print("✅ Logged out successfully")
        return {"message": "Logged out successfully"}
    except Exception as e:
        print(f"❌ Error during logout: {e}")
        return {"message": "Logout completed (with minor issues)"}


@app.get("/auth/status")
async def auth_status():
    """Check authentication status"""
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
            pass

    return {"authenticated": is_authenticated, "user": user_info}


@app.get("/drive/files")
async def get_files(page_size: int = 50, page_token: Optional[str] = None, query: Optional[str] = None):
    """List files from Google Drive"""
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


@app.get("/drive/files/{file_id}")
async def get_file(file_id: str):
    """Get specific file details"""
    try:
        if not drive_client.creds:
            raise HTTPException(status_code=401, detail="Not authenticated")

        file = drive_client.get_file(file_id)
        tags = tagger.generate_tags(file["name"], file.get("mimeType"), file.get("description"))
        return {**file, "aiTags": tags, "type": tagger.detect_file_type(file.get("mimeType", ""))}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/drive/connection-status")
async def connection_status():
    """Get Google Drive connection status"""
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


@app.get("/tags")
async def get_all_tags():
    """Get all available tags"""
    return {"categories": list(tagger.CATEGORIES.keys()), "contentTags": list(tagger.CONTENT_KEYWORDS.keys())}


# For local development
if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Knowledge Hub Backend...")
    print(f"📁 Using .env file: {os.path.join(os.path.dirname(__file__), '.env')}")
    print(f"🌐 API Base URL: {config.SERVICE_API_BASE_URL}")
    print(f"💻 Frontend URL: {config.FRONTEND_URL}")
    print("=" * 60)

    uvicorn.run("main:app", host=config.BACKEND_HOST, port=config.BACKEND_PORT, log_level="info", reload=True)

# For Vercel serverless (IMPORTANT: This must be present)
handler = app