"""
Shared dependencies for the application
"""
from fastapi import Depends, HTTPException
from app.services.google_drive_service import GoogleDriveClient
import os

# Initialize a global drive client
drive_client = None

def init_drive_client():
    """Initialize the global drive client"""
    global drive_client
    if drive_client is None:
        try:
            drive_client = GoogleDriveClient()
            if os.getenv("VERCEL_ENV") != "production":
                drive_client.load_credentials()
            else:
                drive_client.load_credentials()
            print("✅ Drive client initialized in dependencies")
        except Exception as e:
            print(f"⚠️ Could not initialize drive client: {e}")
            drive_client = None
    return drive_client

def get_drive_client():
    """Dependency to get the shared drive client"""
    client = init_drive_client()
    if not client or not client.creds:
        raise HTTPException(status_code=401, detail="Not authenticated with Google Drive")
    return client

def get_current_user_email(drive_client: GoogleDriveClient = Depends(get_drive_client)):
    """Get current user email from Google Drive"""
    try:
        about = drive_client.service.about().get(fields='user').execute()
        user_email = about['user']['emailAddress']
        return user_email
    except Exception as e:
        print(f"⚠️ Error getting current user: {e}")
        return None