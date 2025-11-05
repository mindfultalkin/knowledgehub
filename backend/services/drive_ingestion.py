"""
Google Drive Ingestion Service
Syncs files from Google Drive to database
"""
from typing import Optional, List, Dict
from datetime import datetime
from sqlalchemy.orm import Session
from google_drive import GoogleDriveClient
from models.metadata import (
    Document, 
    ProcessingQueue, 
    SyncCheckpoint, 
    TaskType, 
    ProcessingStatus
)

import hashlib
import config


class DriveIngestionService:
    """
    Service to ingest Google Drive files into database
    """
    
    def __init__(self, drive_client: GoogleDriveClient, db: Session):
        self.drive_client = drive_client
        self.db = db
        
    def sync_all_files(self) -> Dict:
        """
        Sync all files from Google Drive to database
        Returns: {total_files, new_files, updated_files, errors}
        """
        print("🔄 Starting full sync from Google Drive...")
        
        stats = {
            "total_files": 0,
            "new_files": 0,
            "updated_files": 0,
            "errors": 0,
            "skipped": 0
        }
        
        try:
            page_token = None
            
            while True:
                # Get files from Drive
                results = self.drive_client.list_files(
                    page_size=100,
                    page_token=page_token
                )
                
                files = results.get('files', [])
                stats["total_files"] += len(files)
                
                # Process each file
                for file in files:
                    try:
                        result = self._process_file(file)
                        if result == "new":
                            stats["new_files"] += 1
                        elif result == "updated":
                            stats["updated_files"] += 1
                        elif result == "skipped":
                            stats["skipped"] += 1
                    except Exception as e:
                        print(f"❌ Error processing file {file.get('name')}: {e}")
                        stats["errors"] += 1
                
                # Check for next page
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
                print(f"✅ Processed {stats['total_files']} files so far...")
            
            # Save sync checkpoint
            self._save_checkpoint(stats)
            
            print(f"🎉 Sync complete: {stats}")
            return stats
            
        except Exception as e:
            print(f"❌ Sync failed: {e}")
            stats["errors"] += 1
            return stats
    
    def _process_file(self, file_data: Dict) -> str:
        """
        Process a single file from Google Drive
        Returns: 'new', 'updated', or 'skipped'
        """
        drive_file_id = file_data.get('id')
        
        # Check if file already exists in database
        existing_doc = self.db.query(Document).filter(
            Document.drive_file_id == drive_file_id
        ).first()
        
        # Extract metadata
        file_metadata = self._extract_metadata(file_data)
        
        if existing_doc:
            # Check if file was modified
            drive_modified = file_data.get('modifiedTime')
            db_modified = existing_doc.modified_at.isoformat() if existing_doc.modified_at else None
            
            if drive_modified and drive_modified != db_modified:
                # Update existing document
                for key, value in file_metadata.items():
                    setattr(existing_doc, key, value)
                
                existing_doc.db_updated_at = datetime.utcnow()
                self.db.commit()
                
                # Queue for reprocessing
                self._queue_processing_tasks(drive_file_id)
                
                print(f"🔄 Updated: {file_data.get('name')}")
                return "updated"
            else:
                return "skipped"
        else:
            # Create new document
            new_doc = Document(**file_metadata)
            self.db.add(new_doc)
            self.db.commit()
            
            # Queue for processing
            self._queue_processing_tasks(drive_file_id)
            
            print(f"✅ Added: {file_data.get('name')}")
            return "new"
    
    def _extract_metadata(self, file_data: Dict) -> Dict:
        """
        Extract metadata from Google Drive file data
        """
        # Parse timestamps
        created_time = file_data.get('createdTime')
        modified_time = file_data.get('modifiedTime')
        
        created_at = datetime.fromisoformat(created_time.replace('Z', '+00:00')) if created_time else None
        modified_at = datetime.fromisoformat(modified_time.replace('Z', '+00:00')) if modified_time else None
        
        # Extract owner info
        owners = file_data.get('owners', [])
        owner_email = owners[0].get('emailAddress') if owners else None
        owner_name = owners[0].get('displayName') if owners else None
        
        # Get file extension
        file_name = file_data.get('name', '')
        file_format = self._get_file_extension(file_name)
        
        metadata = {
            'id': file_data.get('id'),
            'drive_file_id': file_data.get('id'),
            'title': file_name,
            'mime_type': file_data.get('mimeType'),
            'file_format': file_format,
            'size_bytes': int(file_data.get('size', 0)) if file_data.get('size') else None,
            'owner_email': owner_email,
            'owner_name': owner_name,
            'file_url': file_data.get('webViewLink'),
            'thumbnail_link': file_data.get('thumbnailLink'),
            'icon_link': file_data.get('iconLink'),
            'created_at': created_at,
            'modified_at': modified_at,
            'status': 'active',
            'db_created_at': datetime.utcnow(),
            'db_updated_at': datetime.utcnow()
        }
        
        return metadata
    
    def _get_file_extension(self, filename: str) -> Optional[str]:
        """Extract file extension"""
        if '.' in filename:
            return '.' + filename.rsplit('.', 1)[1].lower()
        return None
    
    def _queue_processing_tasks(self, document_id: str):
        """
        Queue processing tasks for a document
        """
        tasks = [
            TaskType.EXTRACT_TEXT,
            TaskType.AI_TAGGING,
            TaskType.CREATE_EMBEDDING
        ]
        
        for task_type in tasks:
            # Check if task already exists
            existing_task = self.db.query(ProcessingQueue).filter(
                ProcessingQueue.document_id == document_id,
                ProcessingQueue.task_type == task_type,
                ProcessingQueue.status.in_([ProcessingStatus.PENDING, ProcessingStatus.PROCESSING])
            ).first()
            
            if not existing_task:
                new_task = ProcessingQueue(
                    document_id=document_id,
                    task_type=task_type,
                    status=ProcessingStatus.PENDING,
                    priority=5 if task_type == TaskType.EXTRACT_TEXT else 7
                )
                self.db.add(new_task)
        
        self.db.commit()
    
    def _save_checkpoint(self, stats: Dict):
        """
        Save sync checkpoint
        """
        checkpoint = SyncCheckpoint(
            source='google_drive',
            last_sync_time=datetime.utcnow(),
            files_processed=stats.get('total_files', 0),
            files_failed=stats.get('errors', 0),
            status='completed' if stats['errors'] == 0 else 'completed_with_errors'
        )
        self.db.add(checkpoint)
        self.db.commit()
    
    def get_last_sync_info(self) -> Optional[Dict]:
        """
        Get information about last sync
        """
        last_checkpoint = self.db.query(SyncCheckpoint).filter(
            SyncCheckpoint.source == 'google_drive'
        ).order_by(SyncCheckpoint.created_at.desc()).first()
        
        if last_checkpoint:
            return {
                'last_sync_time': last_checkpoint.last_sync_time.isoformat(),
                'files_processed': last_checkpoint.files_processed,
                'files_failed': last_checkpoint.files_failed,
                'status': last_checkpoint.status
            }
        return None
    
    def get_sync_stats(self) -> Dict:
        """
        Get overall sync statistics
        """
        total_docs = self.db.query(Document).count()
        pending_tasks = self.db.query(ProcessingQueue).filter(
            ProcessingQueue.status == ProcessingStatus.PENDING
        ).count()
        
        processing_tasks = self.db.query(ProcessingQueue).filter(
            ProcessingQueue.status == ProcessingStatus.PROCESSING
        ).count()
        
        failed_tasks = self.db.query(ProcessingQueue).filter(
            ProcessingQueue.status == ProcessingStatus.FAILED
        ).count()
        
        return {
            'total_documents': total_docs,
            'pending_tasks': pending_tasks,
            'processing_tasks': processing_tasks,
            'failed_tasks': failed_tasks,
            'last_sync': self.get_last_sync_info()
        }
