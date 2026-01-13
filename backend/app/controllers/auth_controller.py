"""
Authentication and Google Drive auth controllers
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
import os
import asyncio

# Import config
import config

# Import database
from database import get_db

# Import models
from app.models.document import Document

# Import services
from app.services.google_drive_service import GoogleDriveClient
from app.services.drive_ingestion import DriveIngestionService

# Only import dotenv in non-production
if os.getenv("VERCEL_ENV") != "production":
    try:
        from dotenv import set_key
    except ImportError:
        set_key = None

router = APIRouter()

# Initialize Google Drive client
try:
    drive_client = GoogleDriveClient()
    
    if os.getenv("VERCEL_ENV") != "production":
        drive_client.load_credentials()
    else:
        drive_client.load_credentials()
except Exception as e:
    print(f"⚠️ Warning: Could not initialize drive client: {e}")
    drive_client = None

def get_current_user_email():
    """
    Get the currently logged-in user's email from Google Drive
    """
    if not drive_client or not drive_client.creds:
        return None
    
    try:
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
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            # Your extraction logic here
            print("✅ Post-auth extraction completed")
        finally:
            db.close()
    except Exception as e:
        print(f"⚠️ Post-auth extraction failed: {e}")

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
        "redirect_uri": config.GOOGLE_REDIRECT_URIS
    }

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
    """OAuth callback"""
    if not drive_client:
        raise HTTPException(status_code=500, detail="Drive client not initialized")
    
    try:
        print(f"🔗 Exchanging code with redirect URI: {config.GOOGLE_REDIRECT_URIS}")
        drive_client.exchange_code_for_credentials(code, config.GOOGLE_REDIRECT_URIS)
        print("✅ OAuth credentials obtained successfully")
        
        # Try database sync
        try:
            from database import get_db_context
            
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