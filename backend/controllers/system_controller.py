from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import os

import config
from database import get_db
from core.google_client import drive_client
from models.metadata import Document  

# Initialize router
router = APIRouter()


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
    """
    Lightweight system health check
    """
    return {
        "status": "healthy",
        "env": os.getenv("VERCEL_ENV", "local"),
        "GOOGLE_CLIENT_ID_loaded": bool(os.getenv("GOOGLE_CLIENT_ID")),
        "drive_client_available": drive_client is not None,
        "drive_authenticated": drive_client.creds is not None if drive_client else False,
        "redirect_uri": config.GOOGLE_REDIRECT_URIS
    }


# ==================== DATABASE ROUTES ====================

@router.get("/db/health")
async def db_health_check(db: Session = Depends(get_db)):
    """
    Check database health and basic statistics
    """
    try:
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
