from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
import os
import asyncio

import config

# Initialize router
router = APIRouter()

# NOTE:
# We will IMPORT drive_client from api.py to avoid re-initialization
from core.google_client import drive_client
from core.post_auth_tasks import trigger_post_auth_extraction


# Optional dotenv support (local only)
try:
    from dotenv import set_key
except ImportError:
    set_key = None



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
