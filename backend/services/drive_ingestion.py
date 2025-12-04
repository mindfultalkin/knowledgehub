"""
Google Drive Ingestion Service
Syncs files from Google Drive to database with multi-user support
"""
from typing import Optional, List, Dict
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from google_drive import GoogleDriveClient
from models.metadata import (
    Document, 
    ProcessingQueue, 
    SyncCheckpoint, 
    TaskType, 
    ProcessingStatus,
    Tag,
    DocumentTag
)
from tagging import SimpleTagger
import hashlib
import config


class DriveIngestionService:
    """Service to sync Google Drive files to database"""

    def __init__(self, drive_client: GoogleDriveClient, db: Session):
        self.drive_client = drive_client
        self.db = db
        self.tagger = SimpleTagger()
        self._current_user_email = None

    def sync_all_files(self) -> Dict:
        """
        Sync all files from Google Drive to database
        ✅ Each user's files stored with their email
        """
        print("🔄 Starting full sync from Google Drive...")

        # ✅ GET CURRENT USER EMAIL ONCE AT START
        current_user_email = None
        try:
            about = self.drive_client.service.about().get(fields='user').execute()
            current_user_email = about['user']['emailAddress']
            self._current_user_email = current_user_email
            print(f"📧 Syncing for user: {current_user_email}")
        except Exception as e:
            print(f"⚠️ Could not get user: {e}")

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
                results = self.drive_client.list_files(page_size=100, page_token=page_token)
                files = results.get('files', [])

                if not files:
                    break

                stats["total_files"] += len(files)

                for file in files:
                    try:
                        # ✅ PASS EMAIL TO PROCESS FILE
                        result = self._process_file(file, current_user_email)
                        if result == "new":
                            stats["new_files"] += 1
                        elif result == "updated":
                            stats["updated_files"] += 1
                        elif result == "skipped":
                            stats["skipped"] += 1
                    except Exception as e:
                        print(f"❌ Error processing file: {e}")
                        stats["errors"] += 1

                page_token = results.get('nextPageToken')
                if not page_token:
                    break

            self._save_checkpoint(stats)
            print(f"🎉 Sync complete: {stats}")
            return stats

        except Exception as e:
            print(f"❌ Sync failed: {e}")
            import traceback
            print(traceback.format_exc())
            return stats

    def _process_file(self, file_data: Dict, account_email: str = None) -> str:
        """
        Process a single file - ALWAYS create tags even if file unchanged
        ✅ Fixed: Always calls _create_simple_tags
        """
        drive_file_id = file_data.get('id')
        file_name = file_data.get('name', 'Unknown')
        
        # Get modified time from Google Drive
        modified_time_str = file_data.get('modifiedTime')
        if not modified_time_str:
            print(f"⚠️ No modified time for {file_name}, skipping")
            return "skipped"
        
        # Parse modified time (make timezone-aware)
        try:
            modified_time_str = modified_time_str.replace('Z', '+00:00')
            drive_modified_at = datetime.fromisoformat(modified_time_str)
            
            if drive_modified_at.tzinfo is None:
                drive_modified_at = drive_modified_at.replace(tzinfo=timezone.utc)
            
            # ✅ STRIP MICROSECONDS for accurate comparison
            drive_modified_at = drive_modified_at.replace(microsecond=0)
            
        except Exception as e:
            print(f"⚠️ Could not parse time for {file_name}: {e}")
            drive_modified_at = datetime.now(timezone.utc)
        
        try:
            # Check if file exists
            existing_doc = self.db.query(Document).filter(
                Document.drive_file_id == drive_file_id
            ).first()
            
            # ========== THE FIX ==========
            # ALWAYS create/update tags for every file
            self._create_simple_tags(drive_file_id, file_data)
            # ==============================
            
            if existing_doc:
                # Check if file was modified
                db_modified_at = existing_doc.modified_at
                
                if db_modified_at and db_modified_at.tzinfo is None:
                    db_modified_at = db_modified_at.replace(tzinfo=timezone.utc)
                
                # ✅ STRIP MICROSECONDS from DB time too
                if db_modified_at:
                    db_modified_at = db_modified_at.replace(microsecond=0)
                
                if db_modified_at and drive_modified_at <= db_modified_at:
                    # File hasn't changed, but we already created tags above
                    print(f"⏭️  Skipped (unchanged): {file_name}")
                    return "skipped"
                
                # Extract metadata
                file_metadata = self._extract_metadata(file_data, account_email)
                
                # Update existing file
                for key, value in file_metadata.items():
                    setattr(existing_doc, key, value)
                
                existing_doc.db_updated_at = datetime.utcnow()
                self.db.commit()
                
                self._queue_processing_tasks(drive_file_id)
                # Tags already created above
                
                print(f"🔄 Updated: {file_name}")
                return "updated"
            else:
                # Extract metadata
                file_metadata = self._extract_metadata(file_data, account_email)
                
                # New file
                new_doc = Document(**file_metadata)
                self.db.add(new_doc)
                self.db.flush()
                self.db.commit()
                
                self._queue_processing_tasks(drive_file_id)
                # Tags already created above
                
                print(f"✅ Added: {file_name} (User: {account_email})")
                return "new"
        
        except Exception as e:
            print(f"❌ Error processing '{file_name}': {str(e)}")
            import traceback
            print(traceback.format_exc())
            raise

    def _extract_metadata(self, file_data: Dict, account_email: str = None) -> Dict:
        """
        Extract metadata from Google Drive file data
        ✅ NEW: Include account_email to track which user this file belongs to
        """
        # Parse timestamps
        created_time = file_data.get('createdTime')
        modified_time = file_data.get('modifiedTime')

        def parse_iso_time(time_str):
            if not time_str:
                return None
            try:
                time_str = time_str.replace('Z', '+00:00')
                return datetime.fromisoformat(time_str)
            except Exception as e:
                print(f"⚠️ Could not parse time '{time_str}': {e}")
                return None

        created_at = parse_iso_time(created_time)
        modified_at = parse_iso_time(modified_time)

        # Extract owner info
        owners = file_data.get('owners', [])
        owner_email = owners[0].get('emailAddress') if owners else None
        owner_name = owners[0].get('displayName') if owners else None

        # Get file extension
        file_name = file_data.get('name', '')
        file_format = self._get_file_extension(file_name)

        # Create checksum
        checksum = hashlib.md5(
            f"{file_data.get('id')}{modified_time}".encode()
        ).hexdigest()

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
            # ✅ THIS IS THE KEY - Store which account this file belongs to
            'account_email': account_email,
            'account_id': None,
            'checksum': checksum,
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
        Creates 3 tasks per document:
        1. Extract text
        2. AI tagging
        3. Create embeddings
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
                    priority=5 if task_type == TaskType.EXTRACT_TEXT else 7,
                    retry_count=0,
                    max_retries=3
                )
                self.db.add(new_task)

        self.db.commit()

    def _save_checkpoint(self, stats: Dict):
        """
        Save sync checkpoint
        Records when sync happened, how many files, any errors
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
        """Get information about last sync"""
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
        """Get overall sync statistics"""
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

    def _create_simple_tags(self, document_id: str, file_data: Dict):
        """
        Create simple tags based on file type and metadata using SimpleTagger
        Called after document is created/updated
        """
        file_name = file_data.get('name', '')
        mime_type = file_data.get('mimeType', '')
        description = file_data.get('description', '')
        
        # ✅ Use SimpleTagger to generate tags
        tags_to_create = self.tagger.generate_tags(file_name, mime_type, description)
        
        print(f"🏷️  Creating tags for {file_name}: {tags_to_create}")
        
        # ✅ CREATE TAGS IN DATABASE
        for tag_name in set(tags_to_create):  # Remove duplicates
            try:
                # Get or create tag
                tag = self.db.query(Tag).filter(Tag.name == tag_name).first()
                
                if not tag:
                    tag = Tag(
                        name=tag_name,
                        category='simple',  # Mark as simple (not AI)
                        usage_count=0
                    )
                    self.db.add(tag)
                    self.db.flush()  # Get tag ID
                
                # Check if document already has this tag
                existing_doc_tag = self.db.query(DocumentTag).filter(
                    DocumentTag.document_id == document_id,
                    DocumentTag.tag_id == tag.id
                ).first()
                
                if not existing_doc_tag:
                    # Create document-tag relationship
                    doc_tag = DocumentTag(
                        document_id=document_id,
                        tag_id=tag.id,
                        confidence_score=1.0,  # Simple tags = 100% confidence
                        source='rule',  # Mark as rule-based (not ML)
                        created_at=datetime.utcnow()
                    )
                    self.db.add(doc_tag)
                    
                    # Increment tag usage count
                    tag.usage_count += 1
            
            except Exception as e:
                print(f"❌ Error creating tag '{tag_name}': {e}")
        
        self.db.commit()
        print(f"✅ Tags created for {file_name}")

    def _queue_processing_tasks(self, document_id: str):
        """
        Queue processing tasks for a document
        Creates 3 tasks per document:
        1. Extract text
        2. AI tagging
        3. Create embeddings
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
                    priority=5 if task_type == TaskType.EXTRACT_TEXT else 7,
                    retry_count=0,
                    max_retries=3
                )
                self.db.add(new_task)

        self.db.commit()

