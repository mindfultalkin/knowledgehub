"""
Sync controllers
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

# Import services
from database import get_db
from app.services.drive_ingestion import DriveIngestionService
from app.dependencies import get_drive_client, get_current_user_email  # NEW

router = APIRouter()

@router.post("/sync/drive-full")
async def sync_drive_full(
    db: Session = Depends(get_db),
    drive_client = Depends(get_drive_client)
):  # Use dependency injection
    """
    Manually trigger full Google Drive → DB sync.
    """
    try:
        ingestion = DriveIngestionService(drive_client, db)
        stats = ingestion.sync_all_files()
        return {"message": "Sync completed", "stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sync/status")
async def get_sync_status(
    db: Session = Depends(get_db),
    drive_client = Depends(get_drive_client)
):  # Use dependency injection
    """
    Get sync status and statistics
    """
    try:
        ingestion_service = DriveIngestionService(drive_client, db)
        stats = ingestion_service.get_sync_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))